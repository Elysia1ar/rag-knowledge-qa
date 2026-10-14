"""短期记忆：滑动窗口 + 摘要压缩。

设计：
  - Recent Buffer：最近 N 条消息原文，直接进 LLM
  - Summary：更早对话的累积摘要，压缩成一段文本
  - 增量压缩：只压缩尚未摘要的消息，累积到已有 summary
"""
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.chat import Message, Session


logger = get_logger(__name__)


_SUMMARY_PROMPT = """请把以下对话历史压缩成一段简洁的摘要，保留关键信息。

要求：
1. 保留用户提出的所有问题主题
2. 保留重要的结论、事实、决定
3. 保留用户的偏好和特殊要求
4. 忽略寒暄、重复、无关内容
5. 用第三人称描述，如"用户询问了..."、"助手回答了..."
6. 长度控制在 200 字以内

对话历史：
{conversation}

摘要："""


_MERGE_PROMPT = """已有摘要：
{old_summary}

新增对话：
{new_conversation}

请把上述摘要和新增对话合并成新的摘要。
要求：
1. 总长度严格控制在 {max_chars} 字以内
2. 优先保留用户的偏好、关键结论、重要事实
3. 如果超长，删除较早的、已被后续对话覆盖的细节
4. 不要罗列对话流水，要归纳总结

新摘要："""


def _messages_to_text(messages: list[Message]) -> str:
    lines = []
    for m in messages:
        role = "用户" if m.role == "user" else "助手"
        lines.append(f"{role}：{m.content}")
    return "\n".join(lines)


async def _generate_summary(
    old_summary: str | None,
    new_messages: list[Message],
) -> str:
    from app.rag.llm import get_llm

    s = get_settings()
    conversation = _messages_to_text(new_messages)

    if old_summary:
        prompt = _MERGE_PROMPT.format(
            old_summary=old_summary,
            new_conversation=conversation,
            max_chars=s.memory_summary_max_chars,
        )
    else:
        prompt = _SUMMARY_PROMPT.format(conversation=conversation)

    llm = get_llm()
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    text = result.content.strip()

    # 兜底：LLM 不听话时硬截断
    if len(text) > s.memory_summary_max_chars * 1.2:
        text = text[: s.memory_summary_max_chars] + "…"

    return text


async def maybe_compress(
    db: AsyncSession,
    session: Session,
    *,
    buffer_size: int | None = None,
    threshold: int | None = None,
) -> bool:
    """检查并执行摘要压缩。

    Returns:
        True 表示执行了压缩，False 表示未触发。
    """
    s = get_settings()
    buffer_size = buffer_size or s.memory_buffer_size
    threshold = threshold or s.memory_summary_threshold

    stmt = (
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.id)
    )
    result = await db.execute(stmt)
    all_messages = list(result.scalars().all())

    if len(all_messages) <= threshold:
        return False

    # 需要压缩的部分 = 总数 - buffer
    to_compress_end = len(all_messages) - buffer_size
    to_compress = all_messages[:to_compress_end]
    if not to_compress:
        return False

    # 增量：只压缩尚未摘要过的
    already = session.summary_message_count or 0
    new_to_compress = to_compress[already:]
    if not new_to_compress:
        return False

    logger.info(
        "摘要压缩 | session=%s | 新增 %d 条（累计 %d 条）",
        session.id[:8], len(new_to_compress), to_compress_end,
    )

    new_summary = await _generate_summary(session.summary, new_to_compress)

    session.summary = new_summary
    session.summary_message_count = to_compress_end
    await db.commit()

    logger.info(
        "摘要完成 | 长度 %d 字（上限 %d）| 累计覆盖 %d 条",
        len(new_summary), s.memory_summary_max_chars, to_compress_end,
    )

    # 触发记忆固化（从摘要提炼跨轮归纳）
    if session.user_id is not None:
        try:
            from app.memory.consolidate import consolidate_from_summary
            n = await consolidate_from_summary(
                db, session.user_id, new_summary,
                session_id=session.id,
            )
            if n > 0:
                logger.info("固化 %d 条跨轮归纳记忆", n)
        except Exception as e:  # noqa: BLE001
            logger.warning("固化失败：%s", e)

    return True