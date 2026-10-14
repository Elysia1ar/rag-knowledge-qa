"""系统状态汇总。

向量库统计走 Chroma 的 count()，其他走数据库。CPU/IO 密集操作走线程池。
"""
import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.chat import Message, Session
from app.db.models.document import Document
from app.schemas.stats import (
    DocumentStats,
    SessionStats,
    StatsResponse,
    SystemInfo,
    VectorStoreStats,
)


logger = get_logger(__name__)


def _vectorstore_count() -> int:
    """Chroma collection 的向量总数。"""
    from app.rag.vectorstore import get_vectorstore
    try:
        return get_vectorstore()._collection.count()
    except Exception as e:
        logger.warning("统计向量库失败：%s", e)
        return 0


async def collect_stats(db: AsyncSession) -> StatsResponse:
    s = get_settings()

    # ---- 向量库 ----
    total_chunks = await asyncio.to_thread(_vectorstore_count)

    # ---- 文档 ----
    doc_count = (await db.execute(
        select(func.count(Document.id))
    )).scalar_one()

    # ---- 会话 & 消息 ----
    session_count = (await db.execute(
        select(func.count(Session.id))
    )).scalar_one()

    message_count = (await db.execute(
        select(func.count(Message.id))
    )).scalar_one()

    return StatsResponse(
        vectorstore=VectorStoreStats(
            collection=s.chroma_collection,
            total_chunks=total_chunks,
        ),
        documents=DocumentStats(
            total_docs=doc_count,
            total_chunks=total_chunks,   # 同一份数据，向量库里的 chunk 即文档的 chunk
        ),
        sessions=SessionStats(
            total_sessions=session_count,
            total_messages=message_count,
        ),
        system=SystemInfo(
            app_name=s.app_name,
            app_env=s.app_env,
            version="0.1.0",
            embedding_model=s.embedding_model,
            embedding_device=s.embedding_device,
            reranker_enabled=s.reranker_enabled,
            reranker_model=s.reranker_model if s.reranker_enabled else "-",
            llm_provider=s.llm_provider,
            llm_model=s.llm_model,
            chunk_size=s.chunk_size,
            chunk_overlap=s.chunk_overlap,
        ),
    )
