"""问答编排：会话历史 + 查询管线 + 落库。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.rag.pipeline.query_pipeline import QueryResult, run_query
from app.services import session_service
import asyncio

logger = get_logger(__name__)


async def chat(
    db: AsyncSession,
    question: str,
    session_id: str | None = None,
    top_k: int | None = None,
    user_id: int | None = None,
) -> tuple[str, QueryResult]:
    session = await session_service.get_or_create(db, session_id, user_id=user_id)
    await session_service.auto_title_from_question(db, session, question)

    history = await session_service.history_for_condense(db, session.id)
    await session_service.append_message(db, session.id, "user", question)

    # 检索长期记忆
    memory_block = ""
    memory_count = 0
    if user_id is not None:
        from app.memory import long_term
        try:
            memory_block, memory_count = await long_term.build_memory_context(
                db, user_id, question, top_k=3,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("记忆检索失败：%s", e)

    result = await asyncio.to_thread(
        run_query, question, history, top_k, memory_block,
    )
    result.memory_count = memory_count        # ← 挂载到结果对象

    await session_service.append_message(
        db, session.id, "assistant", result.answer, result.sources,
    )

    # 触发摘要压缩（不阻塞主流程）
    try:
        await session_service.maybe_compress(db, session)
    except Exception as e:  # noqa: BLE001
        logger.warning("摘要压缩失败：%s", e)

    # 触发长期记忆提取（用户已登录时）
    if user_id is not None:
        try:
            await _extract_long_term_memories(
                db, user_id, session.id, question,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("长期记忆提取失败：%s", e)

    return session.id, result

async def _extract_long_term_memories(
    db: AsyncSession,
    user_id: int,
    session_id: str,
    latest_question: str,
) -> None:
    """从最近 2 轮对话中提取长期记忆。

    只处理最近的消息，避免重复提取。
    """
    from app.core.config import get_settings
    from app.memory import long_term
    from app.memory.extractor import extract_memories

    s = get_settings()
    if not s.memory_extract_enabled:
        return

    # 取最近 4 条消息（2 轮）用于提取
    messages = await session_service.list_messages(db, session_id)
    recent = messages[-4:] if len(messages) >= 4 else messages

    items = await extract_memories(recent)
    if not items:
        return

    n = await long_term.save_extracted(
        db, user_id, items,
        source_session_id=session_id,
        source_question=latest_question,
    )
    logger.info("自动提取并保存 %d 条长期记忆", n)