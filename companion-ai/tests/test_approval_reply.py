"""Parameterized tests for AgentService._is_approval_reply (AUDIT P-01)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.agent_service import AgentService


# Build a bare instance — we only test the pure approval method.
def _svc() -> AgentService:
    return AgentService.__new__(AgentService)


@pytest.mark.parametrize(
    "text",
    [
        # ---- Chinese rejection (AUDIT P-01 root case) -------------------
        "不可以",
        "不行",
        "不好",
        "不要执行",
        "不同意",
        "坚决不可以",
        "我觉得不可以",
        "不可以吧",
        "别动我电脑",
        "算了",
        # ---- English rejection ------------------------------------------
        "no",
        "no thanks",
        "cancel please",
        "stop",
        "abort it",
        # ---- non-approval neutral / long ---------------------------------
        "",
        "我看看再说",
        "再等一会",
        "yesterday I think this is ok",  # long sentence happens to contain 'ok'
    ],
)
def test_rejects_or_neutral(text):
    assert _svc()._is_approval_reply(text) is False, text


@pytest.mark.parametrize(
    "text",
    [
        "可以",
        "好的",
        "同意",
        "确认",
        "允许",
        "批准",
        "行",
        "没问题",
        "yes",
        "y",
        "ok",
        "okay",
        "sure",
        "confirm",
        "approve",
    ],
)
def test_approves(text):
    assert _svc()._is_approval_reply(text) is True, text
