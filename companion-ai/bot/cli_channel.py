from __future__ import annotations

import asyncio
import getpass
import sys
from collections.abc import Callable

import yaml

from config import config
from core.agent.helpers import coerce_user_id
from core.agent.store import delete_task, task_session_key
from core.messaging.bus import MessageBus
from core.messaging.models import InboundMessage, OutboundMessage
from core.session.manager import SessionManager

_EXIT_COMMANDS = {"/exit", "/quit", "/q"}


class CLIChannel:
    name = "cli"

    def __init__(
        self,
        *,
        bus: MessageBus,
        input_func: Callable[[], str] | None = None,
        output_func: Callable[[str], None] | None = None,
        session: SessionManager | None = None,
        sender: str = "cli-user",
        chat_id: str = "local",
        username: str | None = None,
        agent_name: str = "Alex",
    ) -> None:
        self._bus = bus
        self._input_func = input_func or sys.stdin.readline
        self._output_func = output_func or _default_output
        self._session = session
        self._sender = sender
        self._chat_id = chat_id
        self._username = username or _default_username()
        self._agent_name = agent_name
        self._running = False
        self._bus.subscribe_outbound(self.name, self._on_outbound)

    async def run(self) -> None:
        self._running = True
        self._print_banner()
        try:
            while self._running:
                text = await self._read_line()
                if text == "":
                    break
                stripped = text.strip()
                if not stripped:
                    continue
                if stripped.lower() in _EXIT_COMMANDS:
                    # 退出指令
                    break
                if stripped.startswith("/"):
                    await self._handle_slash_command(stripped)
                    continue
                await self._bus.publish_inbound(
                    InboundMessage(
                        channel=self.name,
                        sender=self._sender,
                        chat_id=self._chat_id,
                        content=stripped,
                        metadata={"username": self._username},
                    )
                )
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self._running = False
            self._output("\n再见！\n")

    async def _handle_slash_command(self, raw: str) -> None:
        """处理控制指令内容"""
        command = raw.split(maxsplit=1)[0].lower()
        if command == "/reset":
            await self._cmd_reset()
        elif command == "/help":
            self._cmd_help()
        else:
            self._output(
                f"\n[未知命令 {command}，输入 /help 查看可用命令]\n"
            )

    async def _cmd_reset(self) -> None:
        user_id = coerce_user_id(self._sender)
        session_key = task_session_key(self.name, self._chat_id)
        if self._session is not None:
            await self._session.clear_history(user_id)
        await delete_task(session_key)
        self._output("\n[已清空 Redis 短期历史与当前 agent 任务状态]\n")

    def _cmd_help(self) -> None:
        text = (
            "可用命令：\n"
            "  /reset           清空当前会话的 Redis 历史与 agent 任务状态\n"
            "  /help            显示帮助\n"
            "  /exit /quit /q   退出 CLI"
        )
        self._output(f"\n{text}\n")

    async def _on_outbound(self, msg: OutboundMessage) -> None:
        """收到消息时调用的回调函数"""
        agent_name = await self._resolve_agent_name()
        self._output(f"\n🤖({agent_name}): {msg.content}\n")
        self._prompt()

    async def _read_line(self) -> str:
        self._prompt()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._input_func)

    def _print_banner(self) -> None:
        self._output(
            "Companion AI CLI | /help 查看命令，/exit 退出\n\n"
        )

    def _prompt(self) -> None:
        self._output(f"🧑({self._username}): ")

    def _output(self, text: str) -> None:
        """终端打印"""
        self._output_func(text)

    async def _resolve_agent_name(self) -> str:
        if self._session is None:
            return self._agent_name

        user = await self._session.get_user(coerce_user_id(self._sender))
        role_id = (user or {}).get("role_id") or self._agent_name
        path = config.ROLES_DIR / f"{role_id}.yaml"
        try:
            with open(path, "r", encoding="utf-8") as f:
                role = yaml.safe_load(f) or {}
            return str(role.get("name") or role_id or self._agent_name)
        except Exception:
            return str(role_id or self._agent_name)


def _default_username() -> str:
    try:
        return getpass.getuser() or "cli"
    except Exception:
        return "cli"


def _default_output(text: str) -> None:
    """将内容 utf8 编码后输出到终端"""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(text, end="", flush=True)
