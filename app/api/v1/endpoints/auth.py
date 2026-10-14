"""认证接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    user = await auth_service.authenticate(db, req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(subject=user.username, role=user.role)
    return LoginResponse(
        access_token=token,
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=UserInfo)
async def me(user: User = Depends(get_current_user)) -> UserInfo:
    return UserInfo(id=user.id, username=user.username, role=user.role)