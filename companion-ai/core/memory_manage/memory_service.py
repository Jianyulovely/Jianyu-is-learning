import logging

from core.memory_manage.memory_model import *
from core.memory_manage.memory_saving import MemorySaver
from core.memory_manage.memory_extraction import MemoryExtractor
from core.memory_manage.memory_summary import MemorySummarizer
from bot.models import ChatTurnContext

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self):
        self.memory_saver = MemorySaver()
        self.memory_extractor = MemoryExtractor()
        self.memory_summarizer = MemorySummarizer()

    async def build_memory_summary(self, memory_query: MemoryQueryContext) -> str:
        """在回复之前 给llm提供关于用户的长期记忆"""
        summary = await self.memory_summarizer.summarize(memory_query)
        mem_summary = (
            f"用户偏好：{summary.preference or '暂无'}\n"
            f"用户背景：{summary.profile or '暂无'}\n"
            f"进行中事项：{summary.ongoing or '暂无'}\n"
            f"重要事件：{summary.event or '暂无'}\n"
        )
        return mem_summary


    async def after_turn(self, chat_turn: ChatTurnContext) -> None:
        """一轮对话结束后，根据用户输入 提取并保存 长期记忆"""
        try:
            memories = await self.memory_extractor.extract(chat_turn)

            if memories:
                await self.memory_saver.save(user_id=chat_turn.user_id, memories=memories)
        except Exception as exc:
            logger.warning("after_turn failed: %s", exc)
