"""Model / tokenizer construction shared by every training and eval script.

Deliberately uses plain transformers + peft (no TRL, no vLLM):
  * fewer moving parts means fewer version-drift breakages;
  * at 1.5B in bf16 we do NOT need 4-bit quantisation on a 16 GB card,
    so bitsandbytes (flakey on Windows) is not required at all.
"""
from __future__ import annotations

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

try:  # peft >= 0.13
    from peft import LoraConfig, PeftModel, get_peft_model
except ImportError as e:  # pragma: no cover
    raise SystemExit("pip install peft>=0.14  (missing peft)") from e


def build_tokenizer(name: str, padding_side: str = "left") -> AutoTokenizer:
    tok = AutoTokenizer.from_pretrained(name, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = padding_side
    return tok


def pick_dtype(cfg: dict) -> torch.dtype:
    """Choose a compute dtype this machine can actually run.

    'auto' = bf16 where the hardware has it (Ampere / sm_80+), else fp32.
    It deliberately does NOT fall back to fp16 on Pascal: sm_61 runs fp16 at
    roughly 1/64 of its fp32 rate, so fp16 there is slower than plain fp32 --
    counter-intuitive, but it is what the hardware does.
    """
    want = str(cfg.get("train", {}).get("dtype", "auto")).lower()
    if want in ("fp32", "float32"):
        return torch.float32
    if want in ("fp16", "float16"):
        return torch.float16
    if want in ("bf16", "bfloat16"):
        return torch.bfloat16
    try:
        if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
            return torch.bfloat16
    except Exception:
        pass
    return torch.float32


def _load_base(name: str, cfg: dict):
    dtype = pick_dtype(cfg)
    print(f"[model] compute dtype: {dtype}")
    kwargs = dict(attn_implementation="sdpa", trust_remote_code=True)
    try:
        model = AutoModelForCausalLM.from_pretrained(name, dtype=dtype, **kwargs)
    except TypeError:  # older transformers only knows torch_dtype
        model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=dtype, **kwargs)
    return model


def build_model(
    name: str,
    cfg: dict,
    adapter_path: str | None = None,
    for_training: bool = False,
):
    """Base model, optionally with a fresh LoRA (training) or a trained adapter."""
    model = _load_base(name, cfg)

    if for_training:
        model.config.use_cache = False
        if cfg["train"]["grad_checkpointing"]:
            model.gradient_checkpointing_enable()
            model.enable_input_require_grads()
        lc = LoraConfig(
            r=cfg["lora"]["r"],
            lora_alpha=cfg["lora"]["alpha"],
            lora_dropout=cfg["lora"]["dropout"],
            target_modules=cfg["lora"]["target_modules"],
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lc)
        model.print_trainable_parameters()

    if adapter_path:
        if not for_training:
            model.config.use_cache = True
        model = PeftModel.from_pretrained(model, adapter_path)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval() if not for_training else model.train()
    return model, device


def tokenizer_for(model) -> AutoTokenizer:
    """peft wraps the base model; dig the tokenizer-free config back out."""
    return model
