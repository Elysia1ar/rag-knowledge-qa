"""会话接口。

所有操作校验归属，非本人的会话返回 404（而非 403，避免泄露存在性）。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.chat import (
    SessionDetail,
    SessionItem,
    SessionRenameRequest,
)
from app.services import session_service


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionItem])
async def list_sessions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SessionItem]:
    """列出当前用户的会话。"""
    rows = await session_service.list_by_user(db, user.id, limit=limit)
    return [
        SessionItem(
            id=s.id,
            title=s.title,
            message_count=count,
            has_summary=bool(s.summary),
            summary_message_count=s.summary_message_count or 0,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s, count in rows
    ]


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionDetail:
    s = await session_service.get_owned_session(db, session_id, user.id)
    if not s:
        raise HTTPException(404, "会话不存在")

    messages = await session_service.list_messages(db, session_id)
    return SessionDetail(
        id=s.id,
        title=s.title,
        created_at=s.created_at.isoformat(),
        updated_at=s.updated_at.isoformat(),
        messages=[
            {"role": m.role, "content": m.content, "sources": m.sources_json}
            for m in messages
        ],
    )


@router.patch("/{session_id}", response_model=SessionItem)
async def rename_session(
    session_id: str,
    req: SessionRenameRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionItem:
    s = await session_service.rename_session(db, session_id, user.id, req.title)
    if not s:
        raise HTTPException(404, "会话不存在")

    messages = await session_service.list_messages(db, session_id)
    return SessionItem(
        id=s.id,
        title=s.title,
        message_count=len(messages),
        created_at=s.created_at.isoformat(),
        updated_at=s.updated_at.isoformat(),
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    ok = await session_service.delete_session(db, session_id, user.id)
    if not ok:
        raise HTTPException(404, "会话不存在")
    return {"code": 0, "message": "deleted"}