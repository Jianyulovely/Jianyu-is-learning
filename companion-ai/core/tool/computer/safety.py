from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


@dataclass(frozen=True)
class SafetyDecision:
    risk: RiskLevel
    reason: str

    @property
    def allowed(self) -> bool:
        return self.risk == RiskLevel.ALLOW


READ_COMMANDS = {
    "cat",
    "cd",
    "dir",
    "echo",
    "findstr",
    "gc",
    "get-childitem",
    "get-command",
    "get-content",
    "get-date",
    "get-item",
    "get-location",
    "get-process",
    "get-service",
    "ls",
    "pwd",
    "select-object",
    "type",
    "where",
    "where-object",
    "whoami",
}

READ_GIT_COMMANDS = {
    "branch",
    "diff",
    "log",
    "show",
    "status",
}

CONFIRM_COMMANDS = {
    "cargo",
    "choco",
    "code",
    "copy",
    "copy-item",
    "curl",
    "del",
    "git",
    "go",
    "iwr",
    "invoke-restmethod",
    "invoke-webrequest",
    "mkdir",
    "move",
    "move-item",
    "new-item",
    "npm",
    "pip",
    "pnpm",
    "python",
    "python3",
    "rd",
    "ren",
    "rename-item",
    "remove-item",
    "rm",
    "rmdir",
    "set-content",
    "start",
    "start-job",
    "start-process",
    "tee-object",
    "wget",
    "yarn",
}

DENY_COMMANDS = {
    "clear-disk",
    "clear-recyclebin",
    "format",
    "reg",
    "stop-computer",
    # 任意代码执行类，全部拉黑
    "invoke-expression",
    "iex",
    "invoke-command",
    "icm",
    "start-job",
    "cmd",
    "cmd.exe",
    "pwsh",
    "pwsh.exe",
    "powershell",
    "powershell.exe",
    "bash",
    "sh",
    "wsl",
    "wsl.exe",
}

DENY_PATTERNS = [
    re.compile(r"\bremove-item\b.*-(recurse|force)", re.IGNORECASE),
    re.compile(r"\brm\b.*(-r|-rf|-fr)", re.IGNORECASE),
    re.compile(r"\bdel\b.*(/s|/q)", re.IGNORECASE),
    re.compile(r"\bformat\b\s+[a-z]:", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\brestart-computer\b", re.IGNORECASE),
    re.compile(r">\s*\$profile\b", re.IGNORECASE),
    # 调用操作符 + 变量 / 字符串 → 任意命令注入
    re.compile(r"(^|[\s|;(])&\s*[\$\"\'(]", re.IGNORECASE),
    # encoded command 绕过
    re.compile(r"-(enc|encodedcommand)\b", re.IGNORECASE),
    # ScriptBlock 动态构造
    re.compile(r"\[scriptblock\]::create", re.IGNORECASE),
    # Add-Type 加载 C# 代码
    re.compile(r"\badd-type\b", re.IGNORECASE),
    # 反射调用
    re.compile(r"\[system\.reflection\.assembly\]", re.IGNORECASE),
    # base64 解码再执行的常见手法
    re.compile(r"frombase64string", re.IGNORECASE),
]

CONFIRM_PATTERNS = [
    re.compile(r"(^|[^>])>\s*\S+", re.IGNORECASE),
    re.compile(r">>\s*\S+", re.IGNORECASE),
    re.compile(r"\|\s*(set-content|out-file|tee-object)\b", re.IGNORECASE),
    # 安装/更新类必须在词首
    re.compile(r"(^|\s)(install|update|upgrade|add)(\s|-|$)", re.IGNORECASE),
    re.compile(r"\b(http|https)://", re.IGNORECASE),
    re.compile(r"\b(start-process|start-job)\b", re.IGNORECASE),
]


def classify_command(command: str) -> SafetyDecision:
    command = command.strip()
    if not command:
        return SafetyDecision(RiskLevel.DENY, "Command is empty.")

    lowered = command.lower()
    for pattern in DENY_PATTERNS:
        if pattern.search(lowered):
            return SafetyDecision(
                RiskLevel.DENY,
                "Command matches a destructive operation that is not supported.",
            )

    commands = _extract_pipeline_commands(command)
    if not commands:
        return SafetyDecision(
            RiskLevel.CONFIRM,
            "Could not confidently classify the command.",
        )

    if any(part in lowered for part in ["&&", "||", ";"]):
        return SafetyDecision(
            RiskLevel.CONFIRM,
            "Compound commands require confirmation.",
        )

    for name, args in commands:
        if name in DENY_COMMANDS:
            return SafetyDecision(
                RiskLevel.DENY,
                f"Command '{name}' is destructive and is not allowed.",
            )

        if name == "git":
            subcommand = args[0].lower() if args else ""
            if subcommand in READ_GIT_COMMANDS:
                continue
            return SafetyDecision(
                RiskLevel.CONFIRM,
                "Git commands that may modify state require confirmation.",
            )

        if name in READ_COMMANDS:
            continue

        if name in CONFIRM_COMMANDS:
            return SafetyDecision(
                RiskLevel.CONFIRM,
                f"Command '{name}' may modify files, install software, access the network, or start a process.",
            )

        return SafetyDecision(
            RiskLevel.CONFIRM,
            f"Command '{name}' is not in the read-only allowlist.",
        )

    for pattern in CONFIRM_PATTERNS:
        if pattern.search(lowered):
            return SafetyDecision(
                RiskLevel.CONFIRM,
                "Command may write files, access the network, install dependencies, or start a long-running process.",
            )

    return SafetyDecision(RiskLevel.ALLOW, "Command appears read-only.")


def _extract_pipeline_commands(command: str) -> list[tuple[str, list[str]]]:
    # NOTE: 不再展开 `powershell -Command "..."` 的 nested payload，否则 LLM
    # 可以借 powershell.exe 包裹任意命令绕过分类。powershell/pwsh/cmd 已经
    # 在 DENY_COMMANDS 中，命中即拒绝。
    commands: list[tuple[str, list[str]]] = []
    for segment in command.split("|"):
        tokens = _split_tokens(segment)
        if not tokens:
            continue
        name = tokens[0].strip().lower()
        commands.append((name, tokens[1:]))
    return commands


def _split_tokens(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=False)
    except ValueError:
        return segment.strip().split()
