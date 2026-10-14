"""轻量级内存任务管理器。

支持后台运行 asyncio 协程、上报进度、取消、查询状态。

限制：进程重启后任务状态丢失，不适合分布式部署。
对于单机项目足够；生产可替换为 Celery / RQ / Arq。
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Literal

from app.core.logging import get_logger


logger = get_logger(__name__)


TaskStatus = Literal["pending", "running", "success", "failed", "cancelled"]


@dataclass
class TaskState:
    id: str
    name: str
    status: TaskStatus = "pending"
    progress: int = 0              # 0~100
    current: int = 0               # 已完成数量
    total: int = 0                 # 总数
    message: str = ""
    error: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "progress": self.progress,
            "current": self.current,
            "total": self.total,
            "message": self.message,
            "error": self.error,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TaskManager:
    """单进程任务管理器。"""

    def __init__(self, max_history: int = 50) -> None:
        self._tasks: dict[str, TaskState] = {}
        self._handles: dict[str, asyncio.Task] = {}
        self._max_history = max_history

    def get(self, task_id: str) -> TaskState | None:
        return self._tasks.get(task_id)

    def list(self, limit: int = 20) -> list[TaskState]:
        items = sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True,
        )
        return items[:limit]

    def _prune(self) -> None:
        """保留最近 N 条已完成任务。"""
        if len(self._tasks) <= self._max_history:
            return
        done = sorted(
            [t for t in self._tasks.values()
             if t.status in ("success", "failed", "cancelled")],
            key=lambda t: t.created_at,
        )
        need = len(self._tasks) - self._max_history
        for t in done[:need]:
            self._tasks.pop(t.id, None)
            self._handles.pop(t.id, None)

    def submit(
        self,
        name: str,
        coro_factory: Callable[["TaskContext"], Awaitable[dict[str, Any] | None]],
    ) -> TaskState:
        """提交一个后台任务。

        coro_factory 接收 TaskContext，返回一个 awaitable，
        运行时可通过 ctx.update(...) 上报进度。
        """
        task_id = uuid.uuid4().hex
        state = TaskState(id=task_id, name=name)
        self._tasks[task_id] = state

        ctx = TaskContext(state=state)

        async def runner() -> None:
            state.status = "running"
            state.updated_at = datetime.now()
            try:
                result = await coro_factory(ctx)
                if ctx.cancelled:
                    state.status = "cancelled"
                    state.message = "任务已取消"
                else:
                    state.status = "success"
                    state.result = result or {}
                    state.message = state.message or "完成"
                    state.progress = 100
            except asyncio.CancelledError:
                state.status = "cancelled"
                state.message = "任务已取消"
                raise
            except Exception as e:  # noqa: BLE001
                logger.exception("任务执行失败: %s", name)
                state.status = "failed"
                state.error = str(e)
            finally:
                state.updated_at = datetime.now()
                self._prune()

        handle = asyncio.create_task(runner())
        self._handles[task_id] = handle
        return state

    def cancel(self, task_id: str) -> bool:
        handle = self._handles.get(task_id)
        state = self._tasks.get(task_id)
        if not handle or not state:
            return False
        if state.status in ("success", "failed", "cancelled"):
            return False
        handle.cancel()
        state.status = "cancelled"
        state.updated_at = datetime.now()
        return True


@dataclass
class TaskContext:
    """任务执行上下文，用于进度上报和取消检查。"""

    state: TaskState
    cancelled: bool = False

    def set_total(self, total: int) -> None:
        self.state.total = total
        self.state.updated_at = datetime.now()

    def update(self, current: int, message: str = "") -> None:
        self.state.current = current
        if self.state.total > 0:
            self.state.progress = int(current / self.state.total * 100)
        if message:
            self.state.message = message
        self.state.updated_at = datetime.now()

    def check_cancel(self) -> None:
        """在任务循环里定期调用，响应取消请求。"""
        if self.cancelled:
            raise asyncio.CancelledError()


# 单例
_manager: TaskManager | None = None


def get_task_manager() -> TaskManager:
    global _manager
    if _manager is None:
        _manager = TaskManager()
    return _manager