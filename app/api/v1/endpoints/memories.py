"""记忆管理接口。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.memory import long_term
from app.memory.forget import run_forget_pipeline


router = APIRouter(prefix="/memories", tags=["memories"])


class MemoryItem(BaseModel):
    id: int
    content: str
    memory_type: str
    importance: float
    access_count: int
    created_at: str


class ForgetResult(BaseModel):
    dedup: int
    time_decay: int
    capacity: int
    total: int


@router.get("", response_model=list[MemoryItem])
async def list_memories(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MemoryItem]:
    mems = await long_term.list_memories(db, user.id, limit=limit)
    return [
        MemoryItem(
            id=m.id, content=m.content, memory_type=m.memory_type,
            importance=m.importance, access_count=m.access_count,
            created_at=m.created_at.isoformat(),
        )
        for m in mems
    ]


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    ok = await long_term.delete_memory_by_id(db, memory_id, user.id)
    return {"code": 0 if ok else 1, "deleted": ok}


@router.post("/forget", response_model=ForgetResult)
async def trigger_forget(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ForgetResult:
    """手动触发遗忘流程。"""
    result = await run_forget_pipeline(db, user.id)
    return ForgetResult(**result)


@router.delete("")
async def clear_all(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    n = await long_term.clear_user_memories(db, user.id)
    return {"code": 0, "deleted": n}