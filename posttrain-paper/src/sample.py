"""Sample K responses per prompt -- the single most expensive step, paid once.

This script is the reason the whole arena fits in ~50 GPU-hours. It writes
three files that all downstream methods consume:

    data/samples.jsonl     every (prompt, response, correct?) triple
    data/rft.jsonl         correct trajectories only          -> train_sft.py
    data/dpo_pairs.jsonl   (chosen, rejected) preference pairs -> train_dpo.py

Usage:
    python src/sample.py --model 1.5B --adapter runs/sft_seed42
    python src/sample.py --model 1.5B --smoke          # 20 prompts, k=2
"""
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    DATA,
    RUNS,
    BudgetTimer,
    extract_answer,
    answers_match,
    append_jsonl,
    format_prompt,
    read_jsonl,
    seed_everything,
    setup_stdout,
    write_jsonl,
    write_json,
)
from configs_loader import load_config  # noqa: E402
from modeling import build_model, build_tokenizer  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="key in config['models'] or a HF id")
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--train-file", default=str(DATA / "train.jsonl"))
    ap.add_argument("--out-dir", default=str(RUNS / "sample"))
    ap.add_argument("--k", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    setup_stdout()

    cfg = load_config()
    seed = args.seed if args.seed is not None else cfg["seeds"][0]
    model_key = args.model or cfg["default_model"]
    model_id = cfg["models"].get(model_key, model_key)
    k = args.k or (2 if args.smoke else cfg["sampling"]["k"])

    seed_everything(seed)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    samples_path = out / "samples.jsonl"
    if samples_path.exists():
        if not args.overwrite:
            raise SystemExit(f"{samples_path} exists; pass --overwrite")
        samples_path.unlink()

    rows = read_jsonl(Path(args.train_file))
    if args.smoke:
        rows = rows[:20]

    tok = build_tokenizer(model_id, padding_side="left")
    model, device = build_model(model_id, cfg, adapter_path=args.adapter)
    model.eval()

    max_new = cfg["sampling"]["max_new_tokens"] if not args.smoke else 128
    bs = cfg["sampling"]["batch_size"] if not args.smoke else 4

    timer = BudgetTimer()
    n_total = 0
    with torch.inference_mode():
        for start in range(0, len(rows), bs):
            chunk = rows[start : start + bs]
            prompts = [format_prompt(tok, r["question"]) for r in chunk]
            enc = tok(prompts, return_tensors="pt", padding=True,
                      truncation=True, max_length=cfg["data"]["max_prompt_tokens"]).to(device)
            for j in range(k):
                with timer.track("sample"):
                    gen = model.generate(
                        **enc,
                        do_sample=True,
                        temperature=cfg["sampling"]["temperature"],
                        top_p=cfg["sampling"]["top_p"],
                        max_new_tokens=max_new,
                        pad_token_id=tok.pad_token_id,
                    )
                new_ids = gen[:, enc["input_ids"].shape[1] :]
                texts = tok.batch_decode(new_ids, skip_special_tokens=True)
                for row, text in zip(chunk, texts):
                    pred = extract_answer(text, "standard")
                    ok = answers_match(pred, row["gold"])
                    append_jsonl(
                        samples_path,
                        {
                            "id": row["id"],
                            "question": row["question"],
                            "gold": row["gold"],
                            "sample_idx": j,
                            "text": text,
                            "pred": pred,
                            "correct": bool(ok),
                        },
                    )
                    n_total += 1
            if (start // bs) % 10 == 0:
                print(f"[sample] {start + len(chunk)}/{len(rows)} prompts, {n_total} samples")

    _derive(out, k, cfg["eval"]["parsers"])
    write_json(out / "meta.json", {
        "model_id": model_id, "adapter": args.adapter, "seed": seed, "k": k,
        "n_prompts": len(rows), "n_samples": n_total, **timer.report(),
    })
    print(f"[sample] done: {n_total} samples -> {samples_path}")
    print(f"[sample] GPU-hours: {timer.gpu_hours():.3f}")


def _derive(out: Path, k: int, parsers: list[str]) -> None:
    """Turn the sample pool into RFT data, DPO pairs, and the training-free baselines.

    Self-consistency comes for free from this same pool: it is the majority vote
    over the K samples already generated, charged at the sampling cost already
    paid. That is why the arena needs only ONE generation pass for four methods.
    """
    rows = read_jsonl(out / "samples.jsonl")
    by_prompt: dict[str, list[dict]] = {}
    for r in rows:
        by_prompt.setdefault(r["id"], []).append(r)

    rft, pairs, stats = [], [], {"prompts": 0, "with_correct": 0, "with_both": 0}
    for pid, group in by_prompt.items():
        stats["prompts"] += 1
        gold = group[0]["gold"]
        correct = [g for g in group if g["correct"]]
        wrong = [g for g in group if not g["correct"]]
        if correct:
            stats["with_correct"] += 1
            for g in correct[:2]:  # cap: don't let easy prompts dominate
                rft.append({"question": g["question"], "target": g["text"], "gold": gold})
        if correct and wrong:
            stats["with_both"] += 1
            for _ in range(min(2, len(correct), len(wrong))):
                c = random.choice(correct)
                w = random.choice(wrong)
                pairs.append({
                    "question": group[0]["question"],
                    "chosen": c["text"],
                    "rejected": w["text"],
                    "gold": gold,
                })

    # ------- training-free baselines, computed from the same samples --------
    baselines: dict[str, dict] = {}
    for mode in parsers:
        n_samples = n_correct = n_found = vote_correct = 0
        for pid, group in by_prompt.items():
            gold = group[0]["gold"]
            preds = [extract_answer(g["text"], mode) for g in group]
            n_samples += len(preds)
            n_correct += sum(answers_match(p, gold) for p in preds)
            n_found += sum(p is not None for p in preds)
            found = [p for p in preds if p is not None]
            if found:
                winner = Counter(found).most_common(1)[0][0]  # ties: first seen
                vote_correct += answers_match(winner, gold)
        baselines[mode] = {
            "per_sample_accuracy": round(n_correct / max(1, n_samples), 4),
            "vote_accuracy": round(vote_correct / max(1, len(by_prompt)), 4),
            "format_compliance": round(n_found / max(1, n_samples), 4),
        }

    write_jsonl(out / "rft.jsonl", rft)
    write_jsonl(out / "dpo_pairs.jsonl", pairs)
    pass_rate = stats["with_correct"] / max(1, stats["prompts"])
    std = baselines["standard"]
    print(f"[sample] prompts with >=1 correct: {stats['with_correct']}/{stats['prompts']} "
          f"({pass_rate:.1%})  [pass@{k}]")
    print(f"[sample] RFT examples={len(rft)}  DPO pairs={len(pairs)}")
    print(f"[sample] baseline (standard parser): per-sample={std['per_sample_accuracy']:.3f} "
          f"self-consistency@{k}={std['vote_accuracy']:.3f}")
    write_json(out / "derive_stats.json", {
        **stats, "pass_at_k": pass_rate, "k": k, "baselines": baselines,
    })


if __name__ == "__main__":
    main()
