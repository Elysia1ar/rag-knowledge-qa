"""索引管理接口（仅 admin）。"""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_admin
from app.db.models.user import User
from app.schemas.index import RebuildRequest, TaskInfo
from app.services import index_service
from app.services.task_manager import get_task_manager


router = APIRouter(prefix="/index", tags=["index"])


@router.post("/rebuild", response_model=TaskInfo)
async def rebuild_index(
    req: RebuildRequest,
    _user: User = Depends(require_admin),
) -> TaskInfo:
    """启动索引重建任务。"""
    mgr = get_task_manager()

    if req.file_path:
        name = f"重建单文件：{req.file_path}"

        async def run(ctx):
            return await index_service.rebuild_single(ctx, req.file_path)

    else:
        name = "全量重建索引"

        async def run(ctx):
            return await index_service.rebuild_all(ctx)

    state = mgr.submit(name, run)
    return TaskInfo(**state.to_dict())


@router.get("/tasks/{task_id}", response_model=TaskInfo)
async def get_task(
    task_id: str,
    _user: User = Depends(require_admin),
) -> TaskInfo:
    mgr = get_task_manager()
    state = mgr.get(task_id)
    if not state:
        raise HTTPException(404, "任务不存在")
    return TaskInfo(**state.to_dict())


@router.get("/tasks", response_model=list[TaskInfo])
async def list_tasks(
    limit: int = 20,
    _user: User = Depends(require_admin),
) -> list[TaskInfo]:
    mgr = get_task_manager()
    return [TaskInfo(**s.to_dict()) for s in mgr.list(limit)]


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    _user: User = Depends(require_admin),
) -> dict:
    mgr = get_task_manager()
    ok = mgr.cancel(task_id)
    return {"code": 0 if ok else 1, "message": "cancelled" if ok else "无法取消"}