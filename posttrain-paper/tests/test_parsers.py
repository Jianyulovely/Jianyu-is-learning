"""Regression tests for the answer-extraction layer.

These run WITHOUT torch/transformers/numpy -- they only exercise src/common.py.
That matters: the parser decides every accuracy number in the paper, so it is
the one component that must be testable on a bare Python install.

    python tests/test_parsers.py

Exit code 0 = all pass.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from common import answers_match, extract_answer  # noqa: E402

EXTRACT_CASES = [
    # (text, mode, expected)
    (r"Let me think." + "\n\n" + r"The answer is \boxed{42}.", "standard", "42"),
    (r"Let me think." + "\n\n" + r"The answer is \boxed{42}.", "strict", "42"),
    ("#### 1,000", "standard", "1000"),
    ("So x = 3/4", "lenient", "3/4"),
    (r"Thus \boxed{\frac{3}{4}}", "standard", "3/4"),
    ("blah", "standard", None),
    (r"\boxed{7}", "strict", None),          # bare answer: strict must reject
    ("The total is 72%.", "lenient", "72"),
    (r"so \boxed{\frac{1}{2}} yes", "standard", "1/2"),
    (r"so \boxed{42", "standard", "42"),      # unclosed brace: must not crash
    ("", "standard", None),
    ("answer is -3.5", "lenient", "-3.5"),
    (r"think twice think twice think \boxed{9}", "strict", "9"),
]

MATCH_CASES = [
    (r"\boxed{1,000}", r"\boxed{1000}", True),
    (r"\boxed{72\%}", r"\boxed{72}", True),
    (r"\boxed{0.5}", r"\boxed{\frac{1}{2}}", True),
    (r"\boxed{18}", r"\boxed{81}", False),
    (None, "3", False),
]


def main() -> int:
    bad = 0
    for text, mode, exp in EXTRACT_CASES:
        got = extract_answer(text, mode)
        ok = got == exp
        bad += not ok
        print(("ok  " if ok else "FAIL"), f"{mode:8s} -> {got!r:12} expected {exp!r}")

    for p, g, exp in MATCH_CASES:
        pp = extract_answer(p, "standard") if p else None
        gg = extract_answer(g, "standard") if g else None
        got = answers_match(pp, gg)
        ok = got == exp
        bad += not ok
        print(("ok  " if ok else "FAIL"), f"match {p} vs {g} -> {got} expected {exp}")

    print(f"\n{len(EXTRACT_CASES) + len(MATCH_CASES) - bad} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
