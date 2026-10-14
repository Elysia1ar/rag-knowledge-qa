"""从对话中提取值得长期记住的信息。

流程：
  1. 把最近若干轮对话交给 LLM
  2. LLM 输出 JSON 数组：[{content, type, importance}]
  3. 过滤掉低于阈值的条目，逐条保存
"""
import json
import re

from langchain_core.messages import HumanMessage

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.chat import Message
from app.rag.llm import get_llm


logger = get_logger(__name__)


_EXTRACT_PROMPT = """从以下对话片段中，提取值得长期记住的用户信息。

只提取**与用户相关的、跨会话仍然有价值**的信息：
- 用户的身份、职业、技能
- 用户的偏好、习惯
- 用户正在做的项目、关注的方向
- 用户的重要结论、决定

**不要提取**：
- 一般性知识问答的内容（例如"RAG 是什么"）
- 寒暄、闲聊
- 助手自己的回答细节

输出格式（JSON 数组，每个元素一行）：
{{"content": "用户偏好 X", "type": "fact|preference|conclusion", "importance": 0.8}}

如果没有值得记住的信息，输出空数组 []。

对话片段：
{conversation}

只输出 JSON 数组，不要其他任何文字："""


def _messages_to_text(messages: list[Message]) -> str:
    lines = []
    for m in messages:
        role = "用户" if m.role == "user" else "助手"
        lines.append(f"{role}：{m.content}")
    return "\n".join(lines)


def _parse_items(raw: str) -> list[dict]:
    """从 LLM 返回里解析 JSON 数组。容错处理。"""
    # 尝试直接 parse
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块里抠
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试抠出第一个 [...] 块
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    return []


async def extract_memories(messages: list[Message]) -> list[dict]:
    """从对话中提取记忆条目。

    Returns:
        [{"content": str, "type": str, "importance": float}, ...]
    """
    if not messages:
        return []

    s = get_settings()
    conversation = _messages_to_text(messages)

    try:
        llm = get_llm()
        result = await llm.ainvoke([
            HumanMessage(content=_EXTRACT_PROMPT.format(conversation=conversation))
        ])
        raw = result.content.strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("提取失败：%s", e)
        return []

    items = _parse_items(raw)
    logger.info("提取到 %d 条候选记忆", len(items))

    # 过滤 + 规范化
    valid: list[dict] = []
    for item in items:
        content = (item.get("content") or "").strip()
        if not content:
            continue

        memory_type = item.get("type", "fact")
        if memory_type not in ("fact", "preference", "conclusion", "event"):
            memory_type = "fact"

        try:
            imp = float(item.get("importance", 0.5))
        except (ValueError, TypeError):
            imp = 0.5

        if imp < s.memory_min_importance:
            logger.debug("丢弃低分记忆(%.2f): %s", imp, content[:30])
            continue

        valid.append({
            "content": content,
            "type": memory_type,
            "importance": imp,
        })

    logger.info("过滤后保留 %d 条", len(valid))
    return valid