"""遗忘机制：语义去重 + 时间衰减 + 容量淘汰。

设计原则：
  - 被访问过的记忆优先保留（access_count > 0）
  - 高重要性的记忆不轻易删
  - 每次操作幂等，可重复调用
"""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.memory import Memory
from app.memory import long_term
from app.rag.vectorstore import get_memory_store


logger = get_logger(__name__)


async def dedup_semantic(
    db: AsyncSession,
    user_id: int,
) -> int:
    """语义去重：相似度 ≥ 阈值时保留高重要性，删低重要性。

    Returns:
        删除的记忆数。
    """
    s = get_settings()
    threshold = s.memory_dedup_threshold

    stmt = (
        select(Memory)
        .where(Memory.user_id == user_id)
        .order_by(Memory.importance.desc(), Memory.id)
    )
    memories = list((await db.execute(stmt)).scalars().all())

    if len(memories) < 2:
        return 0

    vs = get_memory_store()
    to_delete: set[int] = set()

    # 按重要性降序：每条跟已保留的比较
    kept: list[Memory] = []
    for m in memories:
        if m.id in to_delete:
            continue

        duplicate = False
        for k in kept:
            try:
                # 用当前记忆内容去检索，看是否命中已保留的
                hits = vs.similarity_search_with_score(
                    m.content, k=5, filter={"user_id": user_id},
                )
            except Exception:
                break

            for doc, dist in hits:
                mid = doc.metadata.get("memory_id")
                sim = 1.0 - float(dist) / 2.0
                if mid == k.id and sim >= threshold:
                    duplicate = True
                    break
            if duplicate:
                break

        if duplicate:
            to_delete.add(m.id)
            logger.info(
                "去重 | 删除 [%d] imp=%.2f | %s",
                m.id, m.importance, m.content[:50],
            )
        else:
            kept.append(m)

    # 执行删除
    for mid in to_delete:
        await long_term.delete_memory_by_id(db, mid, user_id)

    return len(to_delete)


async def forget_by_time(
    db: AsyncSession,
    user_id: int,
) -> int:
    """时间衰减：删除老且低重要且从未访问的记忆。"""
    s = get_settings()
    cutoff = datetime.now() - timedelta(days=s.memory_forget_max_age_days)

    stmt = select(Memory).where(
        Memory.user_id == user_id,
        Memory.created_at < cutoff,
        Memory.importance < s.memory_forget_min_importance,
        Memory.access_count == 0,
    )
    memories = list((await db.execute(stmt)).scalars().all())

    for m in memories:
        await long_term.delete_memory_by_id(db, m.id, user_id)
        logger.info(
            "时间衰减 | 删除 [%d] age>%d天 imp=%.2f | %s",
            m.id, s.memory_forget_max_age_days, m.importance, m.content[:40],
        )

    return len(memories)


async def forget_by_capacity(
    db: AsyncSession,
    user_id: int,
) -> int:
    """容量淘汰：超过上限时按综合分从低到高删除。"""
    s = get_settings()
    limit = s.memory_max_per_user

    stmt = (
        select(Memory)
        .where(Memory.user_id == user_id)
        .order_by(Memory.importance.desc(), Memory.access_count.desc())
    )
    memories = list((await db.execute(stmt)).scalars().all())

    if len(memories) <= limit:
        return 0

    to_delete = memories[limit:]   # 保留前 limit 条（已按重要性 + 访问次数排序）
    for m in to_delete:
        await long_term.delete_memory_by_id(db, m.id, user_id)
        logger.info(
            "容量淘汰 | 删除 [%d] imp=%.2f ac=%d | %s",
            m.id, m.importance, m.access_count, m.content[:40],
        )

    return len(to_delete)


async def run_forget_pipeline(
    db: AsyncSession,
    user_id: int,
) -> dict:
    """一次性运行所有遗忘策略。"""
    logger.info("遗忘 | user=%d 开始", user_id)

    n_dedup = await dedup_semantic(db, user_id)
    n_time = await forget_by_time(db, user_id)
    n_cap = await forget_by_capacity(db, user_id)

    result = {
        "dedup": n_dedup,
        "time_decay": n_time,
        "capacity": n_cap,
        "total": n_dedup + n_time + n_cap,
    }
    logger.info("遗忘完成 | %s", result)
    return result