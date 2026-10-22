"""Budget-aware LoRA SFT.

The point of this script is the `--budget-gpu-hours` flag: training stops when
the *budget* is spent, not when the model converges. That is what makes the
comparison across methods fair, and it is the central methodological claim of
the paper.

Two modes:
  --steps N                  fixed number of optimizer steps (debug / sweep)
  --budget-gpu-hours H       calibrate throughput, then run exactly H GPU-hours

Usage:
  python src/train_sft.py --model 1.5B --train-file data/train.jsonl --steps 200 --out runs/smoke
  python src/train_sft.py --model 1.5B --train-file data/rft.jsonl --budget-gpu-hours 2 --out runs/rft_b2
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    DATA,
    RUNS,
    BudgetTimer,
    read_jsonl,
    seed_everything,
    setup_stdout,
    write_json,
)
from configs_loader import load_config  # noqa: E402
from modeling import build_model, build_tokenizer  # noqa: E402
from train_common import (  # noqa: E402
    collate,
    infinite_batches,
    make_optimizer,
    make_scheduler,
    save_adapter,
    tokenize_supervised,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--train-file", default=str(DATA / "train.jsonl"))
    ap.add_argument("--out", default=str(RUNS / "sft"))
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--budget-gpu-hours", type=float, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    setup_stdout()

    cfg = load_config()
    seed = args.seed if args.seed is not None else cfg["seeds"][0]
    model_key = args.model or cfg["default_model"]
    model_id = cfg["models"].get(model_key, model_key)
    seed_everything(seed)
    rng = random.Random(seed)

    max_len = cfg["train"]["max_seq_len"]
    tok = build_tokenizer(model_id, padding_side="right")
    rows = read_jsonl(Path(args.train_file))
    if args.smoke:
        rows = rows[:40]

    data = []
    for r in rows:
        ex = tokenize_supervised(tok, r["prompt"] if "prompt" in r else
                                 _prompt_of(tok, r["question"]), r["target"], max_len)
        if ex is not None:
            data.append(ex)
    print(f"[sft] usable examples: {len(data)} / {len(rows)}")

    model, device = build_model(model_id, cfg, for_training=True)
    opt, n_train = make_optimizer(model, args.lr or cfg["train"]["lr_sft"],
                                  cfg["train"]["weight_decay"])
    micro, accum = cfg["train"]["micro_batch"], cfg["train"]["grad_accum"]
    if args.smoke:
        micro, accum = 1, 1

    batch_iter = infinite_batches(data, micro, rng)
    timer = BudgetTimer()

    # ---------------------------------------------------- decide step budget
    budget_h = args.budget_gpu_hours
    if args.smoke:
        max_steps, budget_h = 20, None
    elif args.steps is not None:
        max_steps, budget_h = args.steps, None
    elif budget_h is not None:
        print(f"[sft] calibrating throughput over {cfg['calibration_steps']} steps ...")
        model.train()
        tb = time.perf_counter()
        for _ in range(cfg["calibration_steps"]):
            _train_step(model, [next(batch_iter) for _ in range(accum)], opt,
                        accum, cfg, step=None, sched=None)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        sec_per_step = (time.perf_counter() - tb) / cfg["calibration_steps"]
        n_gpus = max(1, torch.cuda.device_count())
        budget_sec = budget_h * 3600.0 / n_gpus
        max_steps = max(cfg["calibration_steps"] + 1, int(budget_sec / sec_per_step))
        print(f"[sft] {sec_per_step:.3f}s/step -> max_steps={max_steps} for {budget_h}h")
        # fresh optimiser: calibration momentum must not leak into the real run
        opt, n_train = make_optimizer(model, args.lr or cfg["train"]["lr_sft"],
                                      cfg["train"]["weight_decay"])
    else:
        max_steps = 300

    sched = make_scheduler(opt, max_steps, cfg["train"]["warmup_ratio"])
    model.train()

    t0 = time.perf_counter()
    running = 0.0
    for step in range(max_steps):
        batches = [next(batch_iter) for _ in range(accum)]
        loss = _train_step(model, batches, opt, accum, cfg, step, sched)
        running += loss
        if step % 10 == 0 or step == max_steps - 1:
            lr = sched.get_last_lr()[0]
            print(f"[sft] step {step}/{max_steps} loss={running/10:.4f} lr={lr:.2e} "
                  f"elapsed={time.perf_counter()-t0:.0f}s")
            running = 0.0

    elapsed = time.perf_counter() - t0
    n_gpus = max(1, torch.cuda.device_count())
    meta = {
        "method": "sft",
        "model_id": model_id,
        "train_file": args.train_file,
        "seed": seed,
        "max_steps": max_steps,
        "micro_batch": micro,
        "grad_accum": accum,
        "effective_batch": micro * accum,
        "max_seq_len": max_len,
        "lr": args.lr or cfg["train"]["lr_sft"],
        "trainable_params": n_train,
        "n_examples": len(data),
        "wall_seconds": round(elapsed, 2),
        "gpu_hours": round(elapsed * n_gpus / 3600.0, 6),
        "budget_gpu_hours_target": budget_h,
        "budget_minutes_target": round(budget_h * 60, 3) if budget_h else None,
        "calibration_note": "budget = training loop only; excludes data loading and eval",
    }
    save_adapter(model, Path(args.out), meta)
    write_json(Path(args.out) / "budget.json", timer.report())

    # The authoritative budget number is the loop wall clock, not BudgetTimer
    # (BudgetTimer also catches tokenisation, which we exclude on purpose).
    print(f"[sft] done. {meta['gpu_hours']:.3f} GPU-hours, {max_steps} steps")


def _prompt_of(tok, question: str) -> str:
    from common import format_prompt

    return format_prompt(tok, question)


def _train_step(model, batches, opt, accum, cfg, step, sched):
    opt.zero_grad(set_to_none=True)
    total = 0.0
    for b in batches:
        pad_id = model.config.pad_token_id or 0
        t = collate(b, pad_id)
        t = {k: v.to(model.device) for k, v in t.items()}
        out = model(**t)
        loss = out.loss / accum
        loss.backward()
        total += out.loss.item()
    torch.nn.utils.clip_grad_norm_(
        [p for p in model.parameters() if p.requires_grad], cfg["train"]["grad_clip"]
    )
    opt.step()
    if sched is not None:
        sched.step()
    return total / len(batches)


if __name__ == "__main__":
    main()
