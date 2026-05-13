import json
import logging
import re
from config import config

from core.models import ChatRequest
from core.memory_manage.memory_model import *
from core.http_client import safe_post
from core.memory_manage.utils import parse_llm_json_result
from bot.models import ChatTurnContext

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM_PROMPT = """
你是 companion-ai 的长期记忆抽取器。

你的任务是从一轮对话中抽取“未来仍然值得记住的用户信息”。

只允许以下四类记忆：
1. profile: 相对稳定的背景资料
2. preference: 明确偏好、厌恶、习惯
3. ongoing: 持续一段时间的目标、计划、困扰、关系状态
4. event: 近期对后续对话可能重要的事件

不要记录：
- 寒暄
- 一次性小事实
- 助手自己的观点
- 不确定猜测
- 和用户无关的图片内容
- 仅适用于当前一句话、之后几乎没价值的内容

时间规则：
- 你会收到当前请求时间和时区。
- 如果用户提到今天、明天、下周三、月底等相对时间，尽量归一化到 happened_at。
- happened_at 必须是 ISO 8601 字符串，例如 2026-04-30T19:00:00+08:00。
- 如果时间无法可靠确定，happened_at 置为 None。
- 不要把时间戳硬塞进 content，除非时间本身就是关键事实的一部分。

置信度评分：
- 0.9-1.0: 用户明确陈述的事实、偏好或已确认的计划
- 0.75-0.89: 根据用户陈述的合理推断，比较确定的信息
- 0.65-0.74: 根据用户陈述的合理猜测，有一定依据但不完全确定
- below 0.65: 不确定、猜测性很大的推断或及其模糊的表述，不建议保存

输出要求：
- 只能输出 JSON
- 如果没有应保存的内容，输出 {"memories":[]}

输出格式：
{
  "memories": [
    {
      "memory_type": "profile|preference|ongoing|event",
      "content": "简洁中文陈述句，主语默认是用户",
      "keywords": ["关键词1", "关键词2"],
      "confidence": 0.0,
      "happened_at": ""
    }
  ],
}
""".strip()

class MemoryExtractor:
    """对话内容记忆提取器"""
    async def extract(self, chat_turn: ChatTurnContext) -> MemoryList:
        """根据 用户输入内容 提取有关其的 事实性内容 作为长期记忆"""
        image_block = chat_turn.image_context or "无"

        extract_prompt = (                                                                                                                                                                  
            f"当前时间：\n{chat_turn.current_time_iso or '未知'}\n\n"                                                                                                                       
            f"时区：\n{chat_turn.timezone_name}\n\n"                                                                                                                                        
            f"用户输入：\n{chat_turn.user_message}\n\n"                                                                                                                                     
            f"图片上下文：\n{image_block}\n\n"                                                                                                                                              
            "请只从用户输入和图片上下文中抽取长期记忆。"                                                                                                                                    
        )      
        memories = await self._call_llm(extract_prompt)
        return self._filter_candidates(memories)
    
    async def _call_llm(self, prompt: str) -> MemoryCandidateResult:
        req_payload = ChatRequest(
            system_prompt = _EXTRACTION_SYSTEM_PROMPT,
            messages =  [{"role": "user", "content": prompt}],
            response_format =  {
                "type": "json_schema",
                "json_schema": {
                    "name": "memory_candidate_result",
                    "schema": MemoryCandidateResult.model_json_schema()
                }
            },
            temperature =  0.2,
            top_p =  0.9,
        ).model_dump()
        try:
            resp = await safe_post(f"{config.LLM_API_URL}/chat", json=req_payload, timeout=60.0)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("memory extraction llm call failed: %s", exc)
            return MemoryCandidateResult()

        raw_memories = (resp.json().get("reply") or "").strip()
        memories = parse_llm_json_result(
            raw=raw_memories,
            model_cls=MemoryCandidateResult,
            logger=logger
        )
        return memories

    def _filter_candidates(self, candidate_memories: MemoryCandidateResult) -> MemoryList:
        """保留有效类型记忆 同时 去除低置信度(<0.65)记忆内容"""
        results: list[Memory] = []
        candidates = candidate_memories.memories

        for candidate in candidates:
            memory_type = candidate.memory_type
            content = candidate.content.strip()
            if not content:
                continue
            confidence = candidate.confidence
            if confidence < 0.65:
                continue
            keywords = candidate.keywords
            happened_at = candidate.happened_at
            # 仅对包含时间属性记忆类型添加时间戳
            if memory_type in {MemoryType.PROFILE, MemoryType.PREFERENCE}:
                happened_at = None
            memory = Memory(
                memory_type=memory_type,
                content=content,
                keywords=keywords,
                confidence=confidence,
                happened_at=happened_at
            )
            results.append(memory)

        return MemoryList(memories=results)

