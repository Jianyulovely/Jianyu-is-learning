"""StrReplaceEditor: structured file editing tool.

Ported from OpenManus app/tool/str_replace_editor.py. Commands:

  view         — show file content with line numbers, or list a directory
  create       — create a new file (errors if path already exists)
  str_replace  — replace a unique substring with a new one
  insert       — insert a line after a specific line number
  undo_edit    — revert the last edit on a file within this process

Why this exists instead of going through computer_shell:
- LLM works with structured JSON parameters, not PowerShell escaping.
- UTF-8 is hard-coded, so Chinese / Japanese / emoji content writes
  correctly on Windows.
- No shell roundtrip → no command-string approval pairing (AUDIT T-03).
- Path safety enforced once at the boundary via ``ensure_allowed``.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, ClassVar, Literal

from core.tool.base import BaseTool, ToolResult
from core.tool.file_editor.operator import LocalFileOperator
from core.tool.file_editor.safety import ensure_allowed

logger = logging.getLogger(__name__)

Command = Literal["view", "create", "str_replace", "insert", "undo_edit"]

SNIPPET_LINES = 4
MAX_VIEW_CHARS = 8000
_TRUNCATED_NOTICE = (
    "\n<view clipped: file too long. "
    "Re-run view with `view_range` to focus on a subset.>"
)


_DESCRIPTION = """Structured file editor for reading and writing local files.

Prefer this tool over computer_shell whenever you need to create, read, edit,
or list local files. It does not require shell quoting and writes UTF-8.

Commands:
- view: show a file (cat -n style) or a directory listing up to 2 levels.
  Use `view_range` like [11, 50] to scope to a subset of lines (1-based,
  end=-1 means EOF).
- create: create a new file at `path` with `file_text`. Fails if the path
  already exists — use str_replace or insert to modify an existing file.
- str_replace: replace `old_str` with `new_str` inside `path`. `old_str`
  must match EXACTLY ONCE in the file; include enough surrounding context
  to disambiguate. `new_str` defaults to empty string (i.e. deletion).
- insert: insert `new_str` after line `insert_line` (0 = top of file).
- undo_edit: revert the most recent edit on `path` within this session.

`path` must be absolute. Allowed roots: the companion-ai project root,
the user's Desktop/Documents/Downloads, and any directory configured
via the FILE_EDITOR_ALLOWED_DIRS environment variable.
"""


class StrReplaceEditor(BaseTool):
    name: str = "str_replace_editor"
    description: str = _DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["view", "create", "str_replace", "insert", "undo_edit"],
                "description": "Action to perform.",
            },
            "path": {
                "type": "string",
                "description": "Absolute filesystem path.",
            },
            "file_text": {
                "type": "string",
                "description": "Required for command='create'. Full content of the new file.",
            },
            "old_str": {
                "type": "string",
                "description": (
                    "Required for command='str_replace'. Must match exactly once "
                    "in the file. Include enough surrounding context to be unique."
                ),
            },
            "new_str": {
                "type": "string",
                "description": (
                    "Replacement text for str_replace (defaults to empty = delete) "
                    "or the text to insert for insert."
                ),
            },
            "insert_line": {
                "type": "integer",
                "description": (
                    "Required for command='insert'. 0 means top of file; N means "
                    "after the Nth existing line."
                ),
            },
            "view_range": {
                "type": "array",
                "items": {"type": "integer"},
                "description": (
                    "Optional [start, end] line range for view (1-based). "
                    "Use [start, -1] to read from `start` to the end of the file."
                ),
            },
        },
        "required": ["command", "path"],
    }

    # Class-level (ClassVar) so pydantic v2 ignores them as model fields but
    # the dict is shared across all StrReplaceEditor instances — undo state
    # survives the per-step ChatAgent recreation inside PlanningFlow.
    _file_history: ClassVar[dict[str, list[str]]] = defaultdict(list)
    _operator: ClassVar[LocalFileOperator] = LocalFileOperator()

    # In-session marker: an empty-string history entry means "the previous
    # state was 'file did not exist'", so undo deletes the file rather than
    # writing empty text. Real edits push the actual prior content.
    _CREATE_MARKER: ClassVar[str] = "<<__file_editor_create_marker__>>"

    async def execute(
        self,
        *,
        command: Command,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
        **_: Any,
    ) -> ToolResult:
        try:
            resolved = ensure_allowed(Path(path))
        except ValueError as exc:
            return ToolResult(error=str(exc))

        try:
            if command == "view":
                return await self._view(resolved, view_range)
            if command == "create":
                if file_text is None:
                    return ToolResult(error="file_text is required for command='create'")
                return await self._create(resolved, file_text)
            if command == "str_replace":
                if old_str is None:
                    return ToolResult(error="old_str is required for command='str_replace'")
                return await self._str_replace(resolved, old_str, new_str)
            if command == "insert":
                if insert_line is None:
                    return ToolResult(error="insert_line is required for command='insert'")
                if new_str is None:
                    return ToolResult(error="new_str is required for command='insert'")
                return await self._insert(resolved, insert_line, new_str)
            if command == "undo_edit":
                return await self._undo(resolved)
            return ToolResult(error=f"Unknown command: {command}")
        except Exception as exc:  # pragma: no cover - last-resort guard
            logger.exception("file_editor command crashed: %s %s", command, resolved)
            return ToolResult(error=f"file_editor crashed: {exc}")

    # ---- view ----------------------------------------------------------

    async def _view(self, path: Path, view_range: list[int] | None) -> ToolResult:
        if not await self._operator.exists(path):
            return ToolResult(error=f"path does not exist: {path}")
        if await self._operator.is_directory(path):
            if view_range:
                return ToolResult(error="view_range is not allowed when path is a directory.")
            listing = await self._operator.list_directory(path)
            return self.success_response(
                f"Listing of {path} (max depth 2):\n{listing}"
            )

        content = await self._operator.read_file(path)
        init_line = 1
        if view_range:
            if len(view_range) != 2:
                return ToolResult(error="view_range must be [start, end]")
            start, end = view_range
            lines = content.split("\n")
            n = len(lines)
            if start < 1 or start > n:
                return ToolResult(
                    error=f"view_range start {start} out of range [1, {n}]"
                )
            if end != -1 and (end < start or end > n):
                return ToolResult(
                    error=f"view_range end {end} out of range; file has {n} lines."
                )
            content = "\n".join(
                lines[start - 1 :] if end == -1 else lines[start - 1 : end]
            )
            init_line = start

        return self.success_response(_render_with_line_numbers(content, str(path), init_line))

    # ---- create --------------------------------------------------------

    async def _create(self, path: Path, content: str) -> ToolResult:
        if await self._operator.exists(path):
            return ToolResult(
                error=(
                    f"path already exists: {path}. Use str_replace or insert to "
                    "modify an existing file; or pick a different name."
                )
            )
        await self._operator.write_file(path, content)
        self._file_history[str(path)].append(self._CREATE_MARKER)
        return self.success_response(
            f"created {path} ({len(content)} chars, {content.count(chr(10)) + 1} lines)"
        )

    # ---- str_replace ---------------------------------------------------

    async def _str_replace(
        self, path: Path, old_str: str, new_str: str | None
    ) -> ToolResult:
        if not await self._operator.exists(path):
            return ToolResult(error=f"path does not exist: {path}")
        if await self._operator.is_directory(path):
            return ToolResult(error=f"path is a directory: {path}")

        content = (await self._operator.read_file(path)).expandtabs()
        old_norm = old_str.expandtabs()
        new_norm = (new_str or "").expandtabs()

        occurrences = content.count(old_norm)
        if occurrences == 0:
            return ToolResult(
                error=(
                    "old_str not found in file. Re-view the file and include "
                    "enough surrounding context to make the match exact."
                )
            )
        if occurrences > 1:
            line_hits = [
                idx + 1
                for idx, line in enumerate(content.split("\n"))
                if old_norm in line
            ]
            return ToolResult(
                error=(
                    f"old_str appears {occurrences} times "
                    f"(in lines {line_hits[:10]}). "
                    "Include more surrounding context to make it unique."
                )
            )

        new_content = content.replace(old_norm, new_norm)
        await self._operator.write_file(path, new_content)
        self._file_history[str(path)].append(content)

        replacement_line = content.split(old_norm)[0].count("\n")
        snippet_start = max(0, replacement_line - SNIPPET_LINES)
        snippet_end = replacement_line + SNIPPET_LINES + new_norm.count("\n")
        snippet = "\n".join(new_content.split("\n")[snippet_start : snippet_end + 1])
        return self.success_response(
            f"edited {path}\n"
            + _render_with_line_numbers(
                snippet, f"snippet around the edit in {path}", snippet_start + 1
            )
        )

    # ---- insert --------------------------------------------------------

    async def _insert(self, path: Path, insert_line: int, new_str: str) -> ToolResult:
        if not await self._operator.exists(path):
            return ToolResult(error=f"path does not exist: {path}")
        if await self._operator.is_directory(path):
            return ToolResult(error=f"path is a directory: {path}")

        content = (await self._operator.read_file(path)).expandtabs()
        lines = content.split("\n")
        n = len(lines)
        if insert_line < 0 or insert_line > n:
            return ToolResult(
                error=f"insert_line {insert_line} out of range [0, {n}]"
            )

        ins_lines = new_str.expandtabs().split("\n")
        new_lines = lines[:insert_line] + ins_lines + lines[insert_line:]
        new_content = "\n".join(new_lines)
        await self._operator.write_file(path, new_content)
        self._file_history[str(path)].append(content)

        snippet_lines = (
            lines[max(0, insert_line - SNIPPET_LINES) : insert_line]
            + ins_lines
            + lines[insert_line : insert_line + SNIPPET_LINES]
        )
        return self.success_response(
            f"inserted at line {insert_line} of {path}\n"
            + _render_with_line_numbers(
                "\n".join(snippet_lines),
                f"snippet around the insert in {path}",
                max(1, insert_line - SNIPPET_LINES + 1),
            )
        )

    # ---- undo ----------------------------------------------------------

    async def _undo(self, path: Path) -> ToolResult:
        history = self._file_history.get(str(path), [])
        if not history:
            return ToolResult(
                error=f"no edit history for {path} in this session."
            )
        previous = history.pop()
        if previous == self._CREATE_MARKER:
            try:
                await self._operator.delete_file(path)
            except Exception as exc:
                return ToolResult(error=f"undo (delete) failed: {exc}")
            return self.success_response(f"undone create — file {path} deleted.")
        await self._operator.write_file(path, previous)
        return self.success_response(f"undone last edit on {path}.")


def _maybe_truncate(content: str) -> str:
    if len(content) <= MAX_VIEW_CHARS:
        return content
    return content[:MAX_VIEW_CHARS] + _TRUNCATED_NOTICE


def _render_with_line_numbers(content: str, label: str, init_line: int = 1) -> str:
    content = _maybe_truncate(content).expandtabs()
    numbered = "\n".join(
        f"{i + init_line:6d}\t{line}"
        for i, line in enumerate(content.split("\n"))
    )
    return f"`cat -n` style view of {label}:\n{numbered}"
