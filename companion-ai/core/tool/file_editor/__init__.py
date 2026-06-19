"""Structured file editor tool (ported from OpenManus app/tool/str_replace_editor.py).

Prefer this tool over computer_shell for any local file CRUD. See module
docstrings in editor.py / safety.py / operator.py for design rationale.
"""
from core.tool.file_editor.editor import StrReplaceEditor
from core.tool.file_editor.operator import LocalFileOperator
from core.tool.file_editor.safety import (
    PROJECT_ROOT,
    allowed_roots,
    ensure_allowed,
    is_path_allowed,
)

__all__ = [
    "LocalFileOperator",
    "PROJECT_ROOT",
    "StrReplaceEditor",
    "allowed_roots",
    "ensure_allowed",
    "is_path_allowed",
]
