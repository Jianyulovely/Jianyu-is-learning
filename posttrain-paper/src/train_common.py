"""Training helpers shared by train_sft.py and train_dpo.py."""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import torch
from torch.optim import AdamW
from transformers import get_cosine_schedule_with_warmup

PAD_LABEL = -100


def tokenize_supervised(tok, prompt: str, target: str, max_len: int):
    """Concatenate prompt+target, mask the prompt out of the loss."""
    p_ids = tok(prompt, add_special_tokens=False).input_ids
    t_ids = tok(target, add_special_tokens=False).input_ids
    if tok.eos_token_id is not None:
        t_ids = t_ids + [tok.eos_token_id]
    if not t_ids:
        return None
    if len(p_ids) + len(t_ids) > max_len:
        keep = max_len - len(t_ids)
        p_ids = p_ids[-keep:] if keep > 0 else []
        t_ids = t_ids[:max_len]
    input_ids = p_ids + t_ids
    labels = [PAD_LABEL] * len(p_ids) + t_ids
    return {"input_ids": input_ids, "labels": labels}


def tokenize_pair(tok, prompt: str, chosen: str, rejected: str, max_len: int):
    """One preference pair, prompt shared. Returns two supervised examples."""
    a = tokenize_supervised(tok, prompt, chosen, max_len)
    b = tokenize_supervised(tok, prompt, rejected, max_len)
    if a is None or b is None:
        return None
    return a, b


def collate(batch: list[dict], pad_id: int) -> dict:
    width = max(len(b["input_ids"]) for b in batch)
    ids, labels, mask = [], [], []
    for b in batch:
        pad = width - len(b["input_ids"])
        ids.append(b["input_ids"] + [pad_id] * pad)
        labels.append(b["labels"] + [PAD_LABEL] * pad)
        mask.append([1] * len(b["input_ids"]) + [0] * pad)
    return {
        "input_ids": torch.tensor(ids, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
        "attention_mask": torch.tensor(mask, dtype=torch.long),
    }


def infinite_batches(items: list, bs: int, rng: random.Random):
    idx = list(range(len(items)))
    while True:
        rng.shuffle(idx)
        for i in range(0, len(idx), bs):
            yield [items[j] for j in idx[i : i + bs]]


def make_optimizer(model, lr: float, weight_decay: float):
    params = [p for p in model.parameters() if p.requires_grad]
    n = sum(p.numel() for p in params)
    print(f"[train] trainable params: {n:,} ({n/1e6:.2f}M)")
    return AdamW(params, lr=lr, weight_decay=weight_decay), n


def make_scheduler(opt, total_steps: int, warmup_ratio: float):
    warmup = max(1, int(total_steps * warmup_ratio))
    return get_cosine_schedule_with_warmup(opt, warmup, max(1, total_steps))


def save_adapter(model, out: Path, meta: dict) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[train] adapter + meta saved to {out}")


def length_stats(batch: list[dict]) -> dict:
    lens = [len(b["input_ids"]) for b in batch]
    return {"mean_len": sum(lens) / len(lens), "max_len": max(lens)}
