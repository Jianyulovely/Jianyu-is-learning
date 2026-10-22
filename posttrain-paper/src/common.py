"""Shared utilities: seeding, budget timing, answer extraction, JSONL io.

No third-party dependency beyond numpy/torch-at-runtime, so this stays
importable on a bare Python install (useful for tests / table generation).
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RUNS = ROOT / "runs"
for _d in (DATA, RUNS):
    _d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------- seeds
def setup_stdout() -> None:
    """Windows consoles default to GBK; any non-ASCII print then raises
    UnicodeEncodeError. Force UTF-8 with replacement so a stray box-drawing
    character cannot kill a 30-hour run at the last print statement.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def seed_everything(seed: int) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:  # numpy is optional: the parsers and table code must not need it
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except Exception:
        pass


# ------------------------------------------------------------------- budget
class BudgetTimer:
    """Measures wall clock and converts it to GPU-hours.

    Usage:
        t = BudgetTimer()
        with t.track("train"):
            ...
        t.gpu_hours()   # float

    We synchronise the device inside the context manager, otherwise async
    kernel launches make the measurement meaningless.
    """

    def __init__(self) -> None:
        self.spans: dict[str, float] = {}
        self._t0 = time.perf_counter()

    @contextmanager
    def track(self, name: str):
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.synchronize()
        except Exception:
            pass
        start = time.perf_counter()
        try:
            yield
        finally:
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.synchronize()
            except Exception:
                pass
            self.spans[name] = self.spans.get(name, 0.0) + (time.perf_counter() - start)

    def n_gpus(self) -> int:
        try:
            import torch

            return max(1, torch.cuda.device_count())
        except Exception:
            return 1

    def seconds(self, name: str | None = None) -> float:
        if name is None:
            return sum(self.spans.values())
        return self.spans.get(name, 0.0)

    def gpu_hours(self, name: str | None = None) -> float:
        return self.seconds(name) * self.n_gpus() / 3600.0

    def report(self) -> dict:
        return {
            "spans_seconds": dict(self.spans),
            "gpu_hours_total": round(self.gpu_hours(), 6),
            "gpu_hours_by_stage": {
                k: round(v * self.n_gpus() / 3600.0, 6) for k, v in self.spans.items()
            },
            "n_gpus": self.n_gpus(),
        }


# ------------------------------------------------------------ answer parsing
_BOXED_RE = re.compile(r"\\boxed\s*\{")
# a number, optionally a fraction a/b, optionally with thousands separators
_LAST_NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?(?:\s*/\s*-?\d+(?:\.\d+)?)?")
_HASH_RE = re.compile(r"####\s*(.+?)\s*$", re.MULTILINE)
_FRAC_RE = re.compile(r"\\[dt]?frac\{([^{}]+)\}\{([^{}]+)\}")


def _read_braced(text: str, start: int) -> str | None:
    """Return the content of the brace group starting at text[start] == '{'."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i]
    return None


def extract_answer(text: str, mode: str = "standard") -> str | None:
    """Extract a final answer.

    mode="lenient"  : last number anywhere (the generous parser many papers use)
    mode="standard" : last \\boxed{...}, else '#### x', else last number
    mode="strict"   : \\boxed{...} ONLY, and the response must contain a
                      non-trivial reasoning trace before it
    """
    if text is None:
        return None
    text = text.strip()
    # \frac{3}{4} -> 3/4 so every parser sees the same token
    text = _FRAC_RE.sub(r"\1/\2", text)

    if mode == "strict":
        body = text
        pos = body.rfind("\\boxed")
        if pos == -1:
            return None
        brace = body.find("{", pos)
        if brace == -1:
            return None
        ans = _read_braced(body, brace)
        if ans is None:
            return None
        # require some reasoning before the boxed answer.
        # Threshold is a documented heuristic (5 words): bare-answer outputs
        # such as "\\boxed{42}" fail, one-sentence justifications pass.
        # Whatever you choose, state it in the paper's evaluation section.
        if len(body[:pos].split()) < 5:
            return None
        return _normalize(ans)

    if mode in ("standard",):
        pos = text.rfind("\\boxed")
        if pos != -1:
            brace = text.find("{", pos)
            if brace != -1:
                ans = _read_braced(text, brace)
                if ans:
                    return _normalize(ans)
        m = None
        for m in _HASH_RE.finditer(text):
            pass
        if m:
            return _normalize(m.group(1))

    nums = _LAST_NUM_RE.findall(text)
    if nums:
        return _normalize(nums[-1])
    return None


def _normalize(ans: str) -> str:
    a = ans.strip()
    a = a.replace("\\%", "").replace("%", "")
    a = a.replace("$", "").replace(" ", "")
    a = a.replace(",", "")
    # \frac{a}{b} -> a/b
    m = re.fullmatch(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", a)
    if m:
        a = f"{m.group(1)}/{m.group(2)}"
    a = a.rstrip(".")
    return a


def _to_num(s: str) -> float | None:
    """Parse '42', '1,000', '3/4', '-0.5' into a float; None if not numeric."""
    s = s.replace(",", "").strip()
    try:
        if "/" in s:
            a, b = s.split("/", 1)
            den = float(b)
            return float(a) / den if den != 0 else None
        return float(s)
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def answers_match(pred: str | None, gold: str | None, tol: float = 1e-4) -> bool:
    if pred is None or gold is None:
        return False
    p, g = _normalize(pred), _normalize(gold)
    if p == g:
        return True
    pn, gn = _to_num(p), _to_num(g)
    if pn is None or gn is None:
        return False
    return abs(pn - gn) <= tol * max(1.0, abs(gn))


# ---------------------------------------------------------------------- io
def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_json(path: Path, obj: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ------------------------------------------------------------ chat template
def format_prompt(tokenizer, question: str) -> str:
    """Render a user turn with the model's own chat template (no answer)."""
    msgs = [{"role": "user", "content": question}]
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True
        )
    # fallback: ChatML
    return f"<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"


def format_supervised(tokenizer, question: str, answer: str) -> tuple[str, str]:
    """Return (prompt_text, answer_text) -- they get concatenated for SFT."""
    return format_prompt(tokenizer, question), answer.rstrip() + (
        "" if answer.rstrip().endswith(getattr(tokenizer, "eos_token", "") or "\x00") else ""
    )
