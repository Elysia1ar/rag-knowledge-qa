"""系统状态接口（仅 admin）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.stats import StatsResponse
from app.services import stats_service


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> StatsResponse:
    return await stats_service.collect_stats(db)