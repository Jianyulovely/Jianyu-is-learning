"""Load configs/arena.py as a module, with no extra dependency."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | Path | None = None) -> dict:
    p = Path(path) if path else ROOT / "configs" / "arena.py"
    spec = importlib.util.spec_from_file_location("arena_cfg", p)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load config from {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.CONFIG
