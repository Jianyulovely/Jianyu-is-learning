"""Evaluate a checkpoint on GSM8K / MATH-500 with THREE parsers.

Why three parsers
-----------------
The headline accuracy of a math post-training paper depends heavily on how
generously you extract the answer. Reporting only one parser invites the
reviewer to ask whether you picked the flattering one. We always report:

    lenient   last number anywhere            (most generous, most common)
    standard  \\boxed{} else '####' else last  (our main metric)
    strict    \\boxed{} only + real reasoning   (most conservative)

format_compliance = fraction of outputs for which the parser found an answer.
The gap between lenient and strict is the "format dividend" (reused in P2).

Usage:
  python src/eval_math.py --model 1.5B --adapter runs/sft_b2_s42 \
      --method sft --budget 2 --seed 42 --test gsm8k_test
  python src/eval_math.py --model 1.5B --method prompt_only --budget 0 --seed 42 --test math500
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    DATA,
    RUNS,
    answers_match,
    extract_answer,
    format_prompt,
    read_jsonl,
    seed_everything,
    setup_stdout,
    write_json,
    write_jsonl,
)
from configs_loader import load_config  # noqa: E402
from modeling import build_model, build_tokenizer  # noqa: E402

TESTS = {
    "gsm8k_test": DATA / "test_gsm8k.jsonl",
    "math500": DATA / "test_math500.jsonl",
    "dev": DATA / "dev.jsonl",
}


def _blabel(hours: float) -> str:
    """Budget label: minutes when under an hour, hours otherwise.

    The sweep is 5/15/30/60 minutes, so a raw 'b0.0833333' filename would be
    unreadable and would not sort sensibly.
    """
    if 0 < hours < 1:
        return f"{round(hours * 60):g}m"
    return f"{hours:g}h"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--method", required=True, help="sft | rft | dpo | prompt_only | sc")
    ap.add_argument("--budget", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--test", default="gsm8k_test", choices=list(TESTS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--gpu-hours", type=float, default=0.0,
                    help="measured cost of producing this evaluation's samples "
                         "(used only for training-free baselines)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    setup_stdout()

    cfg = load_config()
    seed = args.seed if args.seed is not None else cfg["seeds"][0]
    model_id = cfg["models"].get(args.model or cfg["default_model"], args.model or cfg["default_model"])
    seed_everything(seed)

    rows = read_jsonl(TESTS[args.test])
    if args.smoke:
        rows = rows[:30]
    if args.limit:
        rows = rows[: args.limit]

    tok = build_tokenizer(model_id, padding_side="left")
    model, device = build_model(model_id, cfg, adapter_path=args.adapter)
    model.eval()
    bs = cfg["eval"]["batch_size"] if not args.smoke else 4
    max_new = cfg["eval"]["max_new_tokens"] if not args.smoke else 128

    preds = []
    with torch.inference_mode():
        for start in range(0, len(rows), bs):
            chunk = rows[start : start + bs]
            prompts = [format_prompt(tok, r["question"]) for r in chunk]
            enc = tok(prompts, return_tensors="pt", padding=True, truncation=True,
                      max_length=cfg["data"]["max_prompt_tokens"]).to(device)
            gen = model.generate(
                **enc,
                do_sample=False,
                max_new_tokens=max_new,
                pad_token_id=tok.pad_token_id,
            )
            texts = tok.batch_decode(gen[:, enc["input_ids"].shape[1] :],
                                     skip_special_tokens=True)
            for r, text in zip(chunk, texts):
                preds.append({
                    "id": r["id"],
                    "gold": r["gold"],
                    "text": text,
                    "n_tokens": len(tok(text, add_special_tokens=False).input_ids),
                    "pred": {m: extract_answer(text, m) for m in cfg["eval"]["parsers"]},
                })
            if (start // bs) % 20 == 0:
                print(f"[eval] {start + len(chunk)}/{len(rows)}")

    metrics = {"method": args.method, "budget": args.budget,
               "budget_minutes": round(args.budget * 60, 3) if args.budget else 0,
               "seed": seed,
               "test": args.test, "model_id": model_id, "adapter": args.adapter,
               "gpu_hours": args.gpu_hours, "n": len(preds), "parsers": {}}
    for mode in cfg["eval"]["parsers"]:
        correct = sum(answers_match(p["pred"][mode], p["gold"]) for p in preds)
        found = sum(p["pred"][mode] is not None for p in preds)
        metrics["parsers"][mode] = {
            "accuracy": round(correct / max(1, len(preds)), 4),
            "format_compliance": round(found / max(1, len(preds)), 4),
        }
    metrics["mean_output_tokens"] = round(
        sum(p["n_tokens"] for p in preds) / max(1, len(preds)), 2)

    out = Path(args.out) if args.out else (
        RUNS / "evals" / f"{args.method}_b{_blabel(args.budget)}_s{seed}__{args.test}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(out.with_suffix(".predictions.jsonl"), preds)

    m = metrics["parsers"]
    print(f"[eval] {args.method} b={_blabel(args.budget)} s={seed} {args.test}: "
          f"lenient={m['lenient']['accuracy']:.3f} "
          f"standard={m['standard']['accuracy']:.3f} "
          f"strict={m['strict']['accuracy']:.3f} "
          f"| len={metrics['mean_output_tokens']:.0f}tok")
    print(f"[eval] -> {out}")


if __name__ == "__main__":
    main()
