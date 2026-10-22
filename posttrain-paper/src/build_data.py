"""Build the prompt pools and the two test sets.

Outputs (all under data/):
    train.jsonl        prompts used by SFT / RFT / DPO  {id, question, gold, target}
    dev.jsonl          small held-out slice for any hyperparameter choice
    test_gsm8k.jsonl   {id, question, gold}
    test_math500.jsonl {id, question, gold}

Target format is made uniform on purpose: reasoning text, then a final line
`The answer is \boxed{<gold>}.`  Without that, GSM8K ("#### 18") and MATH
("\\boxed{18}") give the model two different output conventions, and the
format-compliance diagnostic (Table 3 in the protocol) becomes meaningless.

Usage:
    python src/build_data.py            # full
    python src/build_data.py --smoke    # tiny, ~1 min
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, setup_stdout, write_jsonl  # noqa: E402
from configs_loader import load_config  # noqa: E402

GSM8K_HASH = re.compile(r"####\s*(.+?)\s*$", re.MULTILINE)
# GSM8K ships inline calculator annotations, e.g. "7-3=<<7-3=4>>4". Nothing at
# inference time evaluates them, so keeping them in the target teaches the model
# to emit an artifact it can never satisfy -- and hendrycks_math has none, so the
# two sources would disagree on what a reasoning trace looks like.
CALC_ANNOT = re.compile(r"<<.*?>>")


def _strip_calc(text: str) -> str:
    """'He streams for 7-3=<<7-3=4>>4 days' -> 'He streams for 7-3=4 days'.

    The annotation is inserted *before* its own result, so deleting it (rather
    than replacing it with an equals sign) leaves the arithmetic intact:
    "16*10=$<<16*10=160>>160" -> "16*10=$160".
    """
    return re.sub(r"[ \t]{2,}", " ", CALC_ANNOT.sub("", text)).strip()


def gsm8k_to_target(answer_field: str) -> tuple[str, str]:
    """'... reasoning ...\\n#### 18' -> (reasoning, boxed target)."""
    m = GSM8K_HASH.search(answer_field)
    if m:
        gold = m.group(1).strip()
        reasoning = answer_field[: m.start()].strip()
    else:
        gold = answer_field.strip().splitlines()[-1]
        reasoning = answer_field.strip()
    target = f"{_strip_calc(reasoning)}\n\nThe answer is \\boxed{{{gold}}}."
    return gold, target


def _last_boxed(text: str) -> str | None:
    """Read the content of the last \\boxed{...}, brace-balanced.

    EleutherAI/hendrycks_math has NO `answer` column (only problem / level /
    type / solution); the gold is the final \\boxed{...} inside `solution`.
    """
    pos = text.rfind("\\boxed")
    if pos == -1:
        return None
    brace = text.find("{", pos)
    if brace == -1:
        return None
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : i].strip()
    return None


def math_to_target(solution: str) -> tuple[str, str]:
    """hendrycks_math solutions already carry \\boxed{...}; keep them."""
    sol = solution.strip()
    gold = _last_boxed(sol)
    if gold is None:  # no boxed answer: fall back to the last line, and keep
        lines = [ln.strip() for ln in sol.splitlines() if ln.strip()]  # the format uniform
        gold = lines[-1] if lines else ""
        sol = f"{sol}\n\nThe answer is \\boxed{{{gold}}}."
    return gold, sol


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    setup_stdout()

    from datasets import load_dataset

    cfg = load_config()
    rng = random.Random(args.seed)
    n_smoke_train = 60 if args.smoke else None

    # ---------------------------------------------------------------- GSM8K
    print("[data] loading gsm8k ...")
    gsm_train = load_dataset("openai/gsm8k", "main", split="train")
    gsm_test = load_dataset("openai/gsm8k", "main", split="test")

    rows = []
    for i, ex in enumerate(gsm_train):
        gold, target = gsm8k_to_target(ex["answer"])
        rows.append(
            {"id": f"gsm8k_train_{i}", "question": ex["question"], "gold": gold, "target": target}
        )
    rng.shuffle(rows)
    n_keep = n_smoke_train or int(len(rows) * cfg["data"]["train_frac_of_gsm8k"])
    pool = rows[:n_keep]

    # ------------------------------------------------------- extra MATH train
    try:
        print("[data] loading hendrycks_math ...")
        hm = load_dataset("EleutherAI/hendrycks_math", "algebra", split="train")
        extra = []
        for i, ex in enumerate(hm):
            gold, target = math_to_target(ex["solution"])
            extra.append(
                {
                    "id": f"math_train_{i}",
                    "question": ex["problem"],
                    "gold": gold,
                    "target": target,
                }
            )
        rng.shuffle(extra)
        n_extra = 20 if args.smoke else cfg["data"]["extra_math_prompts"]
        pool += extra[:n_extra]
        print(f"[data] +{min(n_extra, len(extra))} MATH train prompts")
    except Exception as e:  # dataset name can move; do not die on it
        print(f"[data] WARNING: could not load hendrycks_math ({e}); GSM8K only")

    rng.shuffle(pool)
    n_dev = max(20, int(len(pool) * cfg["data"]["dev_frac"])) if not args.smoke else 10
    dev, train = pool[:n_dev], pool[n_dev:]

    # ----------------------------------------------------------------- tests
    test_gsm = []
    for i, ex in enumerate(gsm_test):
        gold, _ = gsm8k_to_target(ex["answer"])
        test_gsm.append({"id": f"gsm8k_test_{i}", "question": ex["question"], "gold": gold})
    test_gsm = test_gsm[: (40 if args.smoke else len(test_gsm))]

    test_m500 = []
    try:
        print("[data] loading MATH-500 ...")
        m500 = load_dataset("HuggingFaceH4/MATH-500", split="test")
        for i, ex in enumerate(m500):
            test_m500.append(
                {
                    "id": f"math500_{i}",
                    "question": ex["problem"],
                    "gold": (ex["answer"] or "").strip(),
                }
            )
        test_m500 = test_m500[: (40 if args.smoke else len(test_m500))]
    except Exception as e:
        print(f"[data] WARNING: MATH-500 unavailable ({e}); skipping")

    write_jsonl(DATA / "train.jsonl", train)
    write_jsonl(DATA / "dev.jsonl", dev)
    write_jsonl(DATA / "test_gsm8k.jsonl", test_gsm)
    write_jsonl(DATA / "test_math500.jsonl", test_m500)

    print(f"[data] train={len(train)} dev={len(dev)} "
          f"gsm8k_test={len(test_gsm)} math500={len(test_m500)}")
    print("[data] example target:\n---")
    print(train[0]["target"][:400])
    print("---")


if __name__ == "__main__":
    main()
