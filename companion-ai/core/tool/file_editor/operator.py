"""Local filesystem operator for the structured file editor.

Mirrors OpenManus app/tool/file_operators.py:42-93 LocalFileOperator but:
- Drops the sandbox branch (not relevant here).
- Replaces the Unix-only ``find`` directory listing with a pure-Python walker
  so it works on Windows too.
- Always reads/writes UTF-8 (fixes the Windows GBK encoding pitfall flagged
  in AUDIT X-03).
- Creates intermediate directories on write so an LLM can do
  ``D:\\data\\new_dir\\file.txt`` in one shot.
"""
from __future__ import annotations

import logging
from pathlib import Path

from core.tool.base import ToolError

logger = logging.getLogger(__name__)


class LocalFileOperator:
    """Plain ``Path``-based reads and writes, UTF-8 only."""

    encoding: str = "utf-8"

    async def read_file(self, path: Path) -> str:
        try:
            return path.read_text(encoding=self.encoding)
        except UnicodeDecodeError as exc:
            raise ToolError(
                f"Failed to read {path} as UTF-8: {exc}. "
                "The file is likely binary or in a non-UTF-8 encoding."
            ) from None
        except Exception as exc:
            raise ToolError(f"Failed to read {path}: {exc}") from None

    async def write_file(self, path: Path, content: str) -> None:
        try:
            # Ensure parent directories exist so we can write D:\new_dir\file.txt
            # in a single tool call without first running mkdir.
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding=self.encoding)
        except Exception as exc:
            raise ToolError(f"Failed to write {path}: {exc}") from None

    async def delete_file(self, path: Path) -> None:
        try:
            path.unlink()
        except Exception as exc:
            raise ToolError(f"Failed to delete {path}: {exc}") from None

    async def is_directory(self, path: Path) -> bool:
        return path.is_dir()

    async def exists(self, path: Path) -> bool:
        return path.exists()

    async def list_directory(self, path: Path, max_depth: int = 2) -> str:
        """Return a tree-style listing up to ``max_depth`` deep.

        Replaces OpenManus' ``find -maxdepth 2`` shell call which doesn't
        exist on Windows. Hidden entries (starting with ``.``) are skipped.
        """
        if not path.is_dir():
            return f"Not a directory: {path}"

        lines: list[str] = []

        def walk(current: Path, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                entries = sorted(
                    current.iterdir(),
                    key=lambda x: (not x.is_dir(), x.name.lower()),
                )
            except PermissionError:
                lines.append(f"{'  ' * depth}<permission denied>")
                return
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                indent = "  " * depth
                suffix = "/" if entry.is_dir() else ""
                lines.append(f"{indent}{entry.name}{suffix}")
                if entry.is_dir():
                    walk(entry, depth + 1)

        walk(path, 0)
        return "\n".join(lines) if lines else "(empty)"
