"""Budget-aware LoRA DPO on (chosen, rejected) pairs sampled from the SAME pool.

Reference model = the base model with the adapter disabled (peft's
`model.disable_adapter()`), so no second copy of the weights is needed.
That is what keeps this inside 16 GB.

Usage:
  python src/train_dpo.py --model 1.5B --pairs data/dpo_pairs.jsonl \
      --budget-gpu-hours 4 --seed 42 --out runs/dpo_b4_s42
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, RUNS, read_jsonl, seed_everything, setup_stdout  # noqa: E402
from configs_loader import load_config  # noqa: E402
from modeling import build_model, build_tokenizer  # noqa: E402
from train_common import (  # noqa: E402
    PAD_LABEL,
    collate,
    infinite_batches,
    make_optimizer,
    make_scheduler,
    save_adapter,
    tokenize_pair,
)


def seq_logps(model, t: dict) -> torch.Tensor:
    """Sum of log-probs over the response tokens only."""
    out = model(input_ids=t["input_ids"], attention_mask=t["attention_mask"])
    logits = out.logits[:, :-1, :]
    tgt = t["input_ids"][:, 1:]
    lp = logits.log_softmax(-1).gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
    mask = (t["labels"][:, 1:] != PAD_LABEL).to(lp.dtype)
    return (lp * mask).sum(-1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--pairs", default=str(RUNS / "sample" / "dpo_pairs.jsonl"))
    ap.add_argument("--out", default=str(RUNS / "dpo"))
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--budget-gpu-hours", type=float, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--beta", type=float, default=None)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    setup_stdout()

    cfg = load_config()
    seed = args.seed if args.seed is not None else cfg["seeds"][0]
    model_id = cfg["models"].get(args.model or cfg["default_model"], args.model or cfg["default_model"])
    beta = args.beta if args.beta is not None else cfg["dpo"]["beta"]
    seed_everything(seed)
    rng = random.Random(seed)

    rows = read_jsonl(Path(args.pairs))[: cfg["dpo"]["max_pairs"]]
    if args.smoke:
        rows = rows[:40]
    if not rows:
        raise SystemExit(
            f"no preference pairs at {args.pairs}. Run src/sample.py first "
            "(it derives rft.jsonl and dpo_pairs.jsonl from the same samples)."
        )

    max_len = cfg["train"]["max_seq_len"]
    tok = build_tokenizer(model_id, padding_side="right")

    from common import format_prompt

    data = []
    for r in rows:
        p = format_prompt(tok, r["question"])
        ex = tokenize_pair(tok, p, r["chosen"], r["rejected"], max_len)
        if ex is not None:
            data.append(ex)
    print(f"[dpo] usable pairs: {len(data)} / {len(rows)}")

    model, device = build_model(model_id, cfg, for_training=True)
    opt, n_train = make_optimizer(model, args.lr or cfg["train"]["lr_dpo"],
                                  cfg["train"]["weight_decay"])
    micro, accum = cfg["train"]["micro_batch"], cfg["train"]["grad_accum"]
    if args.smoke:
        micro, accum = 1, 1
    pad_id = tok.pad_token_id or 0

    batch_iter = infinite_batches(data, micro, rng)

    if args.smoke:
        max_steps, budget_h = 20, None
    elif args.steps is not None:
        max_steps, budget_h = args.steps, None
    elif args.budget_gpu_hours is not None:
        budget_h = args.budget_gpu_hours
        print(f"[dpo] calibrating over {cfg['calibration_steps']} steps ...")
        tb = time.perf_counter()
        for _ in range(cfg["calibration_steps"]):
            _dpo_step(model, [next(batch_iter) for _ in range(accum)], opt, accum,
                      cfg, beta, pad_id, sched=None)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        sps = (time.perf_counter() - tb) / cfg["calibration_steps"]
        n_gpus = max(1, torch.cuda.device_count())
        max_steps = max(cfg["calibration_steps"] + 1,
                        int(budget_h * 3600.0 / n_gpus / sps))
        print(f"[dpo] {sps:.3f}s/step -> max_steps={max_steps} for {budget_h}h")
        # fresh optimiser: calibration momentum must not leak into the real run
        opt, n_train = make_optimizer(model, args.lr or cfg["train"]["lr_dpo"],
                                      cfg["train"]["weight_decay"])
    else:
        max_steps, budget_h = 200, None

    sched = make_scheduler(opt, max_steps, cfg["train"]["warmup_ratio"])
    model.train()

    t0 = time.perf_counter()
    running = 0.0
    for step in range(max_steps):
        batches = [next(batch_iter) for _ in range(accum)]
        loss = _dpo_step(model, batches, opt, accum, cfg, beta, pad_id, sched)
        running += loss
        if step % 10 == 0 or step == max_steps - 1:
            print(f"[dpo] step {step}/{max_steps} loss={running/10:.4f} "
                  f"lr={sched.get_last_lr()[0]:.2e} elapsed={time.perf_counter()-t0:.0f}s")
            running = 0.0

    elapsed = time.perf_counter() - t0
    n_gpus = max(1, torch.cuda.device_count())
    meta = {
        "method": "dpo",
        "model_id": model_id,
        "pairs_file": args.pairs,
        "seed": seed,
        "beta": beta,
        "max_steps": max_steps,
        "micro_batch": micro,
        "grad_accum": accum,
        "effective_batch": micro * accum,
        "max_seq_len": max_len,
        "lr": args.lr or cfg["train"]["lr_dpo"],
        "trainable_params": n_train,
        "n_pairs": len(data),
        "wall_seconds": round(elapsed, 2),
        "gpu_hours": round(elapsed * n_gpus / 3600.0, 6),
        "budget_gpu_hours_target": budget_h,
        "budget_minutes_target": round(budget_h * 60, 3) if budget_h else None,
        "note": "reference policy = base model with adapter disabled (no extra weights)",
    }
    save_adapter(model, Path(args.out), meta)
    print(f"[dpo] done. {meta['gpu_hours']:.3f} GPU-hours, {max_steps} steps")


def _dpo_step(model, pairs, opt, accum, cfg, beta, pad_id, sched):
    opt.zero_grad(set_to_none=True)
    total = 0.0
    for chunk in pairs:
        flat = [p[0] for p in chunk] + [p[1] for p in chunk]
        t = collate(flat, pad_id)
        t = {k: v.to(model.device) for k, v in t.items()}
        n = len(chunk)

        pi = seq_logps(model, t)
        pi_c, pi_r = pi[:n], pi[n:]

        with torch.no_grad():
            with model.disable_adapter():
                ref = seq_logps(model, t)
        ref_c, ref_r = ref[:n], ref[n:]

        logits = beta * ((pi_c - pi_r) - (ref_c - ref_r))
        loss = (-F.logsigmoid(logits)).mean() / accum
        loss.backward()
        total += loss.item() * accum

    torch.nn.utils.clip_grad_norm_(
        [p for p in model.parameters() if p.requires_grad], cfg["train"]["grad_clip"]
    )
    opt.step()
    if sched is not None:
        sched.step()
    return total / len(pairs)


if __name__ == "__main__":
    main()
