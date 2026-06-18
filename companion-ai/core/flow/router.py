"""Lightweight control-command detection for plan flows.

All keyword matching goes through ``_normalize`` which lowers + strips
punctuation, so "取消计划！" / "继续。" / "go on please" all map to the same form.
"""
from __future__ import annotations

import re

# Normalize: lowercase, strip whitespace, strip ASCII + common CJK punctuation.
_PUNCT_RE = re.compile(r"[\s\W_]+", flags=re.UNICODE)


def _normalize(text: str) -> str:
    return _PUNCT_RE.sub("", text.strip().lower())


_PLAN_STATUS = {
    "计划状态",
    "查看计划",
    "当前计划",
    "任务状态",
    "进度",
    "status",
    "planstatus",
    "where",
}

_PLAN_CANCEL = {
    "取消计划",
    "停止任务",
    "取消任务",
    "停止计划",
    "终止任务",
    "放弃任务",
    "停止",
    "终止",
    "放弃",
    "算了",
    "cancel",
    "stop",
    "abort",
    "forgetit",
}

_PLAN_CONTINUE = {
    "继续",
    "继续执行",
    "继续吧",
    "下一步",
    "下一个",
    "继续下一步",
    "goon",
    "continue",
    "next",
    "proceed",
}


def is_plan_status_request(text: str) -> bool:
    return _normalize(text) in _PLAN_STATUS


def is_plan_cancel_request(text: str) -> bool:
    return _normalize(text) in _PLAN_CANCEL


def is_plan_continue_request(text: str) -> bool:
    return _normalize(text) in _PLAN_CONTINUE
