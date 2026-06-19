"""Path containment policy for the structured file editor.

Inspired by AUDIT T-01: any local file CRUD must validate that the target
path lives under a known-good root. Unlike the shell tool (which only allows
the project root) the editor opens up commonly-used user directories so
``D:\\data\\notes.txt`` style paths actually work, while still rejecting
arbitrary ``C:\\Windows\\System32`` writes.

Allowed roots (in order, first match wins):
  1. The companion-ai project root (so plan steps inside the repo just work).
  2. The user's ~/Desktop, ~/Documents, ~/Downloads (Path.home() based;
     Windows-friendly).
  3. Anything listed in the ``FILE_EDITOR_ALLOWED_DIRS`` env var,
     comma-separated, absolute paths only.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from config import config

logger = logging.getLogger(__name__)

# 项目根：core/tool/file_editor/safety.py → parents[3] = companion-ai/
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _user_dirs() -> list[Path]:
    home = Path.home()
    return [home / "Desktop", home / "Documents", home / "Downloads"]


def _configured_dirs() -> list[Path]:
    raw = getattr(config, "FILE_EDITOR_ALLOWED_DIRS", "") or ""
    out: list[Path] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            resolved = Path(token).expanduser().resolve()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Skipping invalid FILE_EDITOR_ALLOWED_DIRS entry %r: %s", token, exc)
            continue
        out.append(resolved)
    return out


def allowed_roots() -> list[Path]:
    """Snapshot of currently allowed roots. Recomputed each call so config
    changes (e.g. test monkeypatch) take effect without restart."""
    return [PROJECT_ROOT, *_user_dirs(), *_configured_dirs()]


def ensure_allowed(path: Path) -> Path:
    """Validate ``path`` is absolute + sits under an allowed root.

    Returns the resolved absolute Path. Raises ValueError otherwise.

    Rejects:
      - paths containing un-expanded ``%VAR%`` / ``$VAR`` / leading ``~``
      - relative paths (LLM should always provide absolute)
      - any absolute path not contained in :func:`allowed_roots`

    Error messages are written to guide the agent toward asking the user
    rather than silently picking a different path (2026-06-18 incident:
    LLM saw "outside the allowed roots" and wrote to Desktop instead of
    surfacing the failure).
    """
    raw = str(path)
    if raw.startswith("~") or "%" in raw or "$" in raw:
        raise ValueError(
            "path may not reference environment variables or home dir; "
            "use a literal absolute path instead. "
            "If the user gave the path verbatim, call ask_human to clarify "
            "where they want the file."
        )
    if not path.is_absolute():
        raise ValueError(
            f"path must be absolute, got {path!r}. "
            "Ask the user for the full absolute path via ask_human."
        )
    resolved = path.resolve()
    roots = allowed_roots()
    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise ValueError(
        f"path {resolved} is outside the allowed roots. "
        f"Allowed roots are: {', '.join(str(r) for r in roots)}. "
        "DO NOT silently retry with a different path. "
        "Use ask_human to either (a) ask the user to add this path to "
        "FILE_EDITOR_ALLOWED_DIRS, or (b) confirm an alternative location "
        "that's already allowed."
    )


def is_path_allowed(path: Path | str) -> bool:
    """Convenience wrapper for callers that just want a boolean."""
    try:
        ensure_allowed(Path(path) if isinstance(path, str) else path)
        return True
    except ValueError:
        return False
