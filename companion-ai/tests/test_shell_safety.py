"""Tests for PowerShell command safety classification + cwd containment.

Covers AUDIT T-01 (cwd project-root enforcement) and T-02 (denylist expansion
for iex / &-call-operator / cmd / encoded commands).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.tool.computer.safety import RiskLevel, classify_command
from core.tool.computer.shell import PROJECT_ROOT, _resolve_cwd


# -----------------------------------------------------------------------
# classify_command
# -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "Get-Date",
        "Get-ChildItem",
        "Get-Content readme.md",
        "git status",
        "git log --oneline",
        "ls",
        "pwd",
    ],
)
def test_allow_read_only_commands(command):
    assert classify_command(command).risk == RiskLevel.ALLOW


@pytest.mark.parametrize(
    "command",
    [
        "iex $payload",
        'invoke-expression "Get-Date"',
        "& $cmd",
        "& $payload",
        "cmd /c del whatever",
        "powershell -EncodedCommand abc",
        "powershell -enc abc",
        "Add-Type -AssemblyName whatever",
        "[scriptblock]::create('x')",
        "Remove-Item -Recurse -Force C:/",
        "rm -rf /",
        "format C:",
        "shutdown /r",
    ],
)
def test_deny_dangerous_commands(command):
    assert classify_command(command).risk == RiskLevel.DENY, command


@pytest.mark.parametrize(
    "command",
    [
        "Set-Content -Path a.txt -Value x",
        "Out-File a.txt",
        "echo hi > file.txt",
        "echo hi >> file.txt",
        "git commit -m foo",
        "pip install requests",
        "npm install",
    ],
)
def test_confirm_writes_and_installs(command):
    assert classify_command(command).risk == RiskLevel.CONFIRM, command


# -----------------------------------------------------------------------
# _resolve_cwd
# -----------------------------------------------------------------------


def test_resolve_cwd_default_is_project_root():
    assert _resolve_cwd(None) == PROJECT_ROOT
    assert _resolve_cwd("") == PROJECT_ROOT


def test_resolve_cwd_allows_relative_inside_project():
    assert _resolve_cwd("core") == (PROJECT_ROOT / "core").resolve()
    assert _resolve_cwd("core/agent") == (PROJECT_ROOT / "core" / "agent").resolve()


@pytest.mark.parametrize(
    "bad",
    [
        # 这些路径不在任何 allowed root 下，应拒绝
        "../../../etc/passwd",
        "C:/Windows/System32",
        # 环境变量引用未展开 → 直接拒绝
        "~/.ssh",
        "%USERPROFILE%",
        "$HOME",
    ],
)
def test_resolve_cwd_rejects_escaping(bad):
    with pytest.raises(ValueError):
        _resolve_cwd(bad)


def test_resolve_cwd_allows_user_desktop():
    # ~/Desktop 是 file_editor 白名单的一部分（哪怕物理目录可能不存在，
    # _resolve_cwd 只校验包含关系；具体的"目录存在"由 _run_command 检查）
    from pathlib import Path

    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        pytest.skip("no Desktop on this machine")
    assert _resolve_cwd(str(desktop)) == desktop.resolve()
