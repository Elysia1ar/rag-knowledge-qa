"""长期记忆：存储、检索、删除。

设计要点：
  - DB + Chroma 双写：DB 存结构化字段，Chroma 存向量
  - Chroma 的 id = str(DB 主键)，保持一致
  - 检索时用 where 过滤 user_id，防止跨用户泄露
"""
from datetime import datetime

from langchain_core.documents import Document
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.memory import Memory
from app.rag.vectorstore import add_memories, delete_memory, get_memory_store
from app.core.config import get_settings

logger = get_logger(__name__)


# ---------- 保存 ----------

async def save_memory(
    db: AsyncSession,
    user_id: int,
    content: str,
    *,
    memory_type: str = "fact",
    importance: float = 0.5,
    source_session_id: str | None = None,
    source_question: str | None = None,
) -> Memory:
    """保存一条记忆：DB 先写，再拿 id 写向量库。"""
    content = content.strip()
    if not content:
        raise ValueError("记忆内容不能为空")

    memory = Memory(
        user_id=user_id,
        content=content,
        memory_type=memory_type,
        importance=max(0.0, min(1.0, importance)),
        source_session_id=source_session_id,
        source_question=source_question,
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)

    # 写向量库
    try:
        doc = Document(
            page_content=content,
            metadata={
                "memory_id": memory.id,
                "user_id": user_id,
                "memory_type": memory_type,
                "importance": memory.importance,
                "created_at": memory.created_at.isoformat(),
            },
        )
        add_memories([doc], ids=[str(memory.id)])
    except Exception as e:  # noqa: BLE001
        logger.warning("写向量库失败（DB 已保存）memory_id=%d: %s", memory.id, e)

    logger.info(
        "保存记忆 | user=%d id=%d type=%s importance=%.2f",
        user_id, memory.id, memory_type, importance,
    )
    return memory


# ---------- 检索 ----------

async def search_memories(
    db: AsyncSession,
    user_id: int,
    query: str,
    top_k: int = 5,
    min_importance: float | None = None,
) -> list[Memory]:
    """检索相关记忆，按综合评分排序。

    流程：
      1. Chroma 取 3 倍候选（带距离分数）
      2. DB 补齐字段 + 重要性过滤
      3. 综合评分（相关性 + 时间 + 重要性 + 频率）
      4. 取 Top-K，更新 access_count
    """
    if not query.strip():
        return []

    s = get_settings()
    if min_importance is None:
        min_importance = s.memory_search_min_importance

    try:
        vs = get_memory_store()
        hits = vs.similarity_search_with_score(
            query,
            k=top_k * 3,
            filter={"user_id": user_id},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("记忆检索失败：%s", e)
        return []

    if not hits:
        return []

    # 提取 (memory_id, distance)
    pairs: list[tuple[int, float]] = []
    for doc, dist in hits:
        mid = doc.metadata.get("memory_id")
        if isinstance(mid, int):
            pairs.append((mid, float(dist)))

    if not pairs:
        return []

    id_to_dist = dict(pairs)

    stmt = select(Memory).where(
        Memory.id.in_(list(id_to_dist.keys())),
        Memory.user_id == user_id,
        Memory.importance >= min_importance,
    )
    memories = list((await db.execute(stmt)).scalars().all())

    # 综合评分
    from app.memory.scoring import memory_score

    scored: list[tuple[Memory, float, float]] = []
    for m in memories:
        dist = id_to_dist.get(m.id, 2.0)
        sim = max(0.0, 1.0 - dist / 2.0)

        if sim < s.memory_search_min_similarity:
            logger.debug("记忆 %d 相似度 %.3f 低于下限，淘汰", m.id, sim)
            continue

        score = memory_score(
            vector_sim=sim,
            created_at=m.created_at,
            importance=m.importance,
            access_count=m.access_count or 0,
        )
        scored.append((m, score, sim))

    if not scored:
        logger.info("记忆检索 | query=%s | 无相关记忆", query[:30])
        return []

    scored.sort(key=lambda x: x[1], reverse=True)

    # 相对过滤：只保留与 Top-1 分数接近的
    top_score = scored[0][1]
    threshold = top_score * s.memory_search_min_ratio
    filtered = [(m, sc, sim) for m, sc, sim in scored if sc >= threshold]

    # 硬上限
    filtered = filtered[: s.memory_search_max_results]

    # 调试日志：显示每条分数与相对比例
    for m, sc, sim in scored:
        ratio = sc / top_score if top_score > 0 else 0
        keep = "✓" if sc >= threshold else "✗"
        logger.info(
            "  %s 记忆 %d | sim=%.3f score=%.4f ratio=%.2f | %s",
            keep, m.id, sim, sc, ratio, m.content[:30],
        )

    # 更新访问统计
    for m, _, _ in filtered:
        m.access_count = (m.access_count or 0) + 1
        m.last_accessed_at = datetime.now()
    if filtered:
        await db.commit()

    logger.info(
        "记忆检索 | query=%s | 候选 %d → 相似度过滤 %d → 相对过滤 %d",
        query[:30], len(memories), len(scored), len(filtered),
    )
    return [m for m, _, _ in filtered]


# ---------- 删除 ----------

async def delete_memory_by_id(
    db: AsyncSession,
    memory_id: int,
    user_id: int,
) -> bool:
    """删除一条记忆（DB + Chroma）。"""
    stmt = select(Memory).where(
        Memory.id == memory_id,
        Memory.user_id == user_id,
    )
    memory = (await db.execute(stmt)).scalar_one_or_none()
    if not memory:
        return False

    await db.delete(memory)
    await db.commit()

    # 向量库尽力删
    try:
        delete_memory(str(memory_id))
    except Exception as e:  # noqa: BLE001
        logger.warning("删向量失败 memory_id=%d: %s", memory_id, e)

    return True


async def list_memories(
    db: AsyncSession,
    user_id: int,
    limit: int = 50,
) -> list[Memory]:
    """列出用户所有记忆（按重要性倒序）。"""
    stmt = (
        select(Memory)
        .where(Memory.user_id == user_id)
        .order_by(Memory.importance.desc(), Memory.id.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def clear_user_memories(db: AsyncSession, user_id: int) -> int:
    """清空用户所有记忆。"""
    stmt = select(Memory).where(Memory.user_id == user_id)
    memories = list((await db.execute(stmt)).scalars().all())

    for m in memories:
        try:
            delete_memory(str(m.id))
        except Exception:  # noqa: BLE001
            pass

    stmt = sql_delete(Memory).where(Memory.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0

async def save_extracted(
    db: AsyncSession,
    user_id: int,
    items: list[dict],
    *,
    source_session_id: str | None = None,
    source_question: str | None = None,
) -> int:
    """批量保存从对话中提取的记忆条目。返回成功保存的数量。"""
    count = 0
    for item in items:
        try:
            await save_memory(
                db, user_id,
                content=item["content"],
                memory_type=item.get("type", "fact"),
                importance=item.get("importance", 0.5),
                source_session_id=source_session_id,
                source_question=source_question,
            )
            count += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("保存记忆失败：%s | %s", item, e)
    return count

async def build_memory_context(
    db: AsyncSession,
    user_id: int,
    query: str,
    top_k: int = 5,
) -> tuple[str, int]:
    """检索记忆并构造 prompt 片段。

    Returns:
        (memory_block, count)
    """
    memories = await search_memories(db, user_id, query, top_k=top_k)
    if not memories:
        return "", 0

    type_label = {
        "fact": "事实",
        "preference": "偏好",
        "conclusion": "结论",
        "event": "事件",
    }

    lines = [
        "## 关于用户的已知信息",
        "（来自历史对话的记忆，优先参考这些信息来回答）",
    ]
    for m in memories:
        label = type_label.get(m.memory_type, "信息")
        lines.append(f"- [{label}] {m.content}")

    return "\n".join(lines), len(memories)