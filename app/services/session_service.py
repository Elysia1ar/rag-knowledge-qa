"""会话 CRUD 服务。

所有操作都要带 user_id 校验归属，避免用户 A 访问用户 B 的会话。
"""
import json
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.chat import Message, Session
from app.core.config import get_settings
from app.memory.short_term import maybe_compress

logger = get_logger(__name__)


async def create_session(
    db: AsyncSession,
    user_id: int | None = None,
    title: str = "新会话",
) -> Session:
    s = Session(id=uuid.uuid4().hex, user_id=user_id, title=title)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def get_session(db: AsyncSession, session_id: str) -> Session | None:
    return await db.get(Session, session_id)


async def get_owned_session(
    db: AsyncSession,
    session_id: str,
    user_id: int,
) -> Session | None:
    """获取会话，且校验归属。用户不匹配时返回 None（由调用方决定如何响应）。"""
    s = await db.get(Session, session_id)
    if not s:
        return None
    if s.user_id is not None and s.user_id != user_id:
        return None
    return s


async def get_or_create(
    db: AsyncSession,
    session_id: str | None,
    user_id: int | None = None,
) -> Session:
    """带 user_id 的 get_or_create。

    - 有 session_id 且归属正确：返回旧会话
    - 有 session_id 但归属错误或不存在：创建新会话（静默，避免信息泄露）
    - 无 session_id：创建新会话
    """
    if session_id and user_id is not None:
        existing = await get_owned_session(db, session_id, user_id)
        if existing:
            return existing
    elif session_id:
        existing = await get_session(db, session_id)
        if existing:
            return existing

    return await create_session(db, user_id=user_id)


async def list_by_user(
    db: AsyncSession,
    user_id: int,
    limit: int = 50,
) -> list[tuple[Session, int]]:
    """列出用户的会话，附带消息数。按 updated_at 倒序。"""
    stmt = (
        select(Session, func.count(Message.id).label("msg_count"))
        .outerjoin(Message, Message.session_id == Session.id)
        .where(Session.user_id == user_id)
        .group_by(Session.id)
        .order_by(Session.updated_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def rename_session(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    title: str,
) -> Session | None:
    s = await get_owned_session(db, session_id, user_id)
    if not s:
        return None
    s.title = title.strip()[:100]
    await db.commit()
    await db.refresh(s)
    return s


async def delete_session(
    db: AsyncSession,
    session_id: str,
    user_id: int,
) -> bool:
    """删除会话及其所有消息（cascade）。"""
    s = await get_owned_session(db, session_id, user_id)
    if not s:
        return False
    await db.delete(s)
    await db.commit()
    logger.info("用户 %d 删除会话 %s", user_id, session_id)
    return True


def _clean_title(question: str, max_len: int = 25) -> str:
    """把用户问题清理成一个简洁的会话标题。"""
    original = question.strip()

    t = question.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    t = " ".join(t.split())
    t = t.rstrip("？?！!。.，,：:；;")

    # 清理后为空（纯标点/空白）→ 用原问题的字符兜底
    if not t:
        if not original:
            return "新会话"
        return original[:max_len] + ("…" if len(original) > max_len else "")

    if len(t) > max_len:
        t = t[:max_len].rstrip() + "…"

    return t


async def auto_title_from_question(
    db: AsyncSession,
    session: Session,
    question: str,
) -> None:
    if session.title not in ("新会话", "", None):
        return
    title = _clean_title(question)
    logger.info(
        "[auto_title] session=%s | question=%r | new_title=%r",
        session.id[:8], question[:40], title,
    )
    if not title:
        return
    session.title = title
    await db.commit()


async def list_messages(db: AsyncSession, session_id: str) -> list[Message]:
    stmt = select(Message).where(Message.session_id == session_id).order_by(Message.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def append_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> Message:
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        sources_json=json.dumps(sources or [], ensure_ascii=False),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def history_for_condense(db: AsyncSession, session_id: str) -> list[dict]:
    """返回对话上下文：summary（若有）+ 最近 buffer。

    优先返回摘要，避免把全量历史塞进 LLM。
    """
    s = get_settings()
    session = await db.get(Session, session_id)
    if not session:
        return []

    messages = await list_messages(db, session_id)
    buffer_size = s.memory_buffer_size

    # 最近 buffer
    recent = messages[-buffer_size:] if len(messages) > buffer_size else messages

    result: list[dict] = []
    if session.summary:
        result.append({
            "role": "system",
            "content": f"【历史对话摘要】\n{session.summary}",
        })
    result.extend({"role": m.role, "content": m.content} for m in recent)
    return result