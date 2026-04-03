"""
模型加载模块 —— 启动时加载一次，全局复用。
P0 阶段：float32，无量化，单 GPU。
"""
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from config import config

_tokenizer = None
_model = None


def load_model():
    global _tokenizer, _model
    if _model is not None:
        return _tokenizer, _model

    print(f"[model_loader] Loading model from {config.MODEL_PATH} ...")
    _tokenizer = AutoTokenizer.from_pretrained(config.MODEL_PATH)
    _model = AutoModelForCausalLM.from_pretrained(
        config.MODEL_PATH,
        dtype=torch.float32,
        device_map=config.CUDA_DEVICE,
    )
    _model.eval()
    mem_gb = torch.cuda.memory_allocated() / 1024**3
    print(f"[model_loader] Model loaded. GPU memory used: {mem_gb:.2f} GB")
    return _tokenizer, _model


def get_model():
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")
    return _tokenizer, _model
