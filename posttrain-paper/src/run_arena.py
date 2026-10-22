"""Sequential driver for the full arena grid.

Deliberately dumb: it shells out to the individual scripts one at a time so a
crash leaves the completed runs on disk and you can resume. It is NOT a job
scheduler -- if you have multiple seeds to run, prefer two terminals / two
`Start-Process` calls, or just re-run this and it skips existing adapters.

  python src/run_arena.py --dry-run        # print the plan, run nothing
  python src/run_arena.py --model 1.5B     # actually run

Order matters: sampling first (it is shared), then training, then eval.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, ROOT, RUNS, setup_stdout  # noqa: E402
from configs_loader import load_config  # noqa: E402

PY = sys.executable
SRC = ROOT / "src"


def run(cmd: list[str], dry: bool) -> None:
    print("$ " + " ".join(cmd), flush=True)
    if dry:
        return
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit(f"command failed with {r.returncode}: {' '.join(cmd)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-sample", action="store_true")
    ap.add_argument("--tests", default="gsm8k_test,math500")
    args = ap.parse_args()
    setup_stdout()

    cfg = load_config()
    model = args.model or cfg["default_model"]
    seeds = [args.seed] if args.seed else cfg["seeds"]
    # The sweep is configured in MINUTES; the internal unit stays GPU-hours so
    # every script keeps one comparable cost measure.
    budget_minutes = cfg["budget_minutes"]
    tests = args.tests.split(",")
    dry = args.dry_run

    sample_dir = RUNS / "sample"
    if not args.skip_sample and not dry:
        if (sample_dir / "samples.jsonl").exists():
            print(f"[arena] reusing existing {sample_dir/'samples.jsonl'}")
        else:
            run([PY, str(SRC / "sample.py"), "--model", model], dry)

    plan = []
    for seed in seeds:
        for bm in budget_minutes:
            hours = bm / 60.0
            for method, script, extra in [
                ("sft", SRC / "train_sft.py", ["--train-file", str(DATA / "train.jsonl")]),
                ("rft", SRC / "train_sft.py", ["--train-file", str(sample_dir / "rft.jsonl")]),
                ("dpo", SRC / "train_dpo.py", []),
            ]:
                out = RUNS / f"{method}_b{bm:g}m_s{seed}"
                if out.exists():
                    print(f"[arena] skip (exists): {out.name}")
                    continue
                plan.append((method, script, extra, bm, hours, seed, out))

    print(f"\n[arena] {len(plan)} training runs planned for model={model}\n")
    for method, script, extra, bm, hours, seed, out in plan:
        cmd = [PY, str(script), "--model", model,
               "--budget-gpu-hours", f"{hours:.6f}",
               "--seed", str(seed), "--out", str(out)] + extra
        run(cmd, dry)

    print("\n[arena] evaluating every produced adapter ...")
    for method in ("sft", "rft", "dpo"):
        for seed in seeds:
            for bm in budget_minutes:
                hours = bm / 60.0
                out = RUNS / f"{method}_b{bm:g}m_s{seed}"
                if not (out / "adapter_model.safetensors").exists():
                    continue
                for test in tests:
                    run([PY, str(SRC / "eval_math.py"), "--model", model,
                         "--adapter", str(out), "--method", method,
                         "--budget", f"{hours:.6f}", "--seed", str(seed),
                         "--test", test], dry)

    # the training-free baselines: run once, budget is irrelevant (set 0)
    for seed in seeds:
        for test in tests:
            run([PY, str(SRC / "eval_math.py"), "--model", model,
                 "--method", "prompt_only", "--budget", "0",
                 "--seed", str(seed), "--test", test], dry)

    print("\n[arena] done. Now: python src/make_tables.py")


if __name__ == "__main__":
    main()
