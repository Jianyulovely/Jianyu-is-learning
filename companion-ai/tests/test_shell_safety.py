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
        "../..",
        "../../../etc/passwd",
        "C:/Users/Administrator",
        "C:/Windows/System32",
        "~/.ssh",
        "%USERPROFILE%",
        "$HOME",
    ],
)
def test_resolve_cwd_rejects_escaping(bad):
    with pytest.raises(ValueError):
        _resolve_cwd(bad)
