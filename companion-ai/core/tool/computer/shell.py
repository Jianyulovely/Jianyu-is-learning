from __future__ import annotations

import asyncio
import shlex
import time
from pathlib import Path
from typing import Any

from core.tool.base import BaseTool, ToolResult
from core.tool.computer.output import build_command_output
from core.tool.computer.safety import RiskLevel, classify_command


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIMEOUT_SECONDS = 15
MAX_TIMEOUT_SECONDS = 60

# 写入类前缀：执行成功后强制追加 Test-Path 验证。
_WRITE_VERIFICATION_MARKERS = (
    "set-content",
    "add-content",
    "out-file",
    "new-item",
    "copy-item",
    "move-item",
    "rename-item",
    "mkdir",
    ">",
    ">>",
)


class ComputerShellTool(BaseTool):
    name: str = "computer_shell"
    description: str = (
        "Run a non-interactive local PowerShell command for computer operation tasks. "
        "Use this only for bounded command-line work. Read-only commands can run directly; "
        "commands that write files, install dependencies, access the network, launch GUI apps, "
        "or start long-running processes will be blocked and should be confirmed with ask_human first. "
        "The working directory is locked under the companion-ai project root."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "PowerShell command to execute.",
            },
            "cwd": {
                "type": "string",
                "description": (
                    "Optional working directory relative to the project root. "
                    "Absolute paths or paths escaping the project root will be rejected."
                ),
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds. Defaults to 15 and is capped at 60.",
                "minimum": 1,
                "maximum": MAX_TIMEOUT_SECONDS,
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    async def execute(
        self,
        *,
        command: str,
        cwd: str | None = None,
        timeout: int | None = None,
        approved_once: bool = False,
        **_: Any,
    ) -> ToolResult:
        command = command.strip()
        if not command:
            return ToolResult(error="Command is empty.")

        # cwd 校验先于 safety，保证越界路径无论命令是否危险都直接拒绝。
        try:
            workdir = _resolve_cwd(cwd)
        except ValueError as exc:
            return ToolResult(error=str(exc))

        if approved_once:
            return await self._run_command(command=command, workdir=workdir, timeout=timeout)

        decision = classify_command(command)
        if decision.risk == RiskLevel.DENY:
            return ToolResult(error=f"Refused to run command: {decision.reason}")
        if decision.risk == RiskLevel.CONFIRM:
            return ToolResult(
                error=(
                    "Command requires human confirmation before execution. "
                    f"Reason: {decision.reason}. Use ask_human to request approval."
                )
            )

        return await self._run_command(command=command, workdir=workdir, timeout=timeout)

    async def _run_command(
        self,
        *,
        command: str,
        workdir: Path,
        timeout: int | None,
    ) -> ToolResult:
        if not workdir.exists() or not workdir.is_dir():
            return ToolResult(error=f"Working directory does not exist: {workdir}")

        timeout_seconds = _normalize_timeout(timeout)
        started = time.perf_counter()
        try:
            process = await asyncio.create_subprocess_exec(
                "powershell",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
                cwd=str(workdir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
            exit_code = process.returncode or 0
        except asyncio.TimeoutError:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            try:
                process.kill()
                await process.communicate()
            except ProcessLookupError:
                pass
            return ToolResult(
                error=(
                    f"Command timed out after {timeout_seconds}s "
                    f"(elapsed_ms={elapsed_ms})."
                )
            )
        except FileNotFoundError:
            return ToolResult(error="PowerShell executable was not found on this machine.")

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        output = build_command_output(
            exit_code=exit_code,
            stdout=_decode(stdout_bytes),
            stderr=_decode(stderr_bytes),
            elapsed_ms=elapsed_ms,
        )
        result_dict: dict[str, object] = output.to_dict()

        # 对写文件类命令补一次 Test-Path 验证，防止 LLM 谎称已完成。
        if exit_code == 0 and _looks_like_write(command):
            verification = await self._verify_write(command=command, workdir=workdir)
            result_dict["verification"] = verification

        return self.success_response(result_dict)

    async def _verify_write(self, *, command: str, workdir: Path) -> dict[str, object]:
        target = _extract_write_target(command)
        if not target:
            return {"status": "skipped", "reason": "Could not infer write target."}

        verify_cmd = f"Test-Path -LiteralPath {shlex.quote(target)}"
        try:
            process = await asyncio.create_subprocess_exec(
                "powershell",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                verify_cmd,
                cwd=str(workdir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )
            stdout_bytes, _ = await asyncio.wait_for(process.communicate(), timeout=10)
            exists = _decode(stdout_bytes).strip().lower() == "true"
            return {
                "status": "ok" if exists else "failed",
                "target": target,
                "exists": exists,
            }
        except Exception as exc:
            return {"status": "failed", "target": target, "error": str(exc)}


def _resolve_cwd(cwd: str | None) -> Path:
    """Resolve cwd under PROJECT_ROOT; reject any path that escapes it.

    Rejects: absolute paths outside project root, paths using ``..`` to escape,
    paths starting with ``~`` or ``$``/``%`` env-var references.
    """
    if not cwd:
        return PROJECT_ROOT

    raw = cwd.strip()
    if not raw:
        return PROJECT_ROOT

    # 禁止环境变量/家目录扩展，避免 %USERPROFILE% / ~ 偷渡
    if raw.startswith("~") or "%" in raw or "$" in raw:
        raise ValueError("cwd may not reference environment variables or home dir.")

    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (PROJECT_ROOT / candidate).resolve()

    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(
            f"cwd must stay within project root {PROJECT_ROOT}, got {resolved}"
        ) from exc

    return resolved


def _normalize_timeout(timeout: int | None) -> int:
    if timeout is None:
        return DEFAULT_TIMEOUT_SECONDS
    return max(1, min(int(timeout), MAX_TIMEOUT_SECONDS))


def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n")


def _looks_like_write(command: str) -> bool:
    lowered = command.lower()
    return any(marker in lowered for marker in _WRITE_VERIFICATION_MARKERS)


def _extract_write_target(command: str) -> str | None:
    """Best-effort extraction of the write target path from a PowerShell command."""
    import re

    patterns = [
        # Set-Content / Out-File / Add-Content / Tee-Object -Path "X"
        re.compile(r"(?:set-content|out-file|add-content|tee-object)[^|]*?-path\s+['\"]?([^\s'\"]+)", re.IGNORECASE),
        # New-Item -Path "X"
        re.compile(r"new-item[^|]*?-path\s+['\"]?([^\s'\"]+)", re.IGNORECASE),
        # Copy-Item / Move-Item / Rename-Item -Destination "X"
        re.compile(r"(?:copy-item|move-item|rename-item)[^|]*?-destination\s+['\"]?([^\s'\"]+)", re.IGNORECASE),
        # mkdir / New-Item 后接位置参数
        re.compile(r"\bmkdir\s+['\"]?([^\s'\"]+)", re.IGNORECASE),
        # 重定向 > / >> 后的目标
        re.compile(r">>?\s*['\"]?([^\s'\"]+)"),
    ]
    for pattern in patterns:
        match = pattern.search(command)
        if match:
            return match.group(1)
    return None
