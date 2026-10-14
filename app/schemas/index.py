"""索引管理相关 Schema。"""
from pydantic import BaseModel


class TaskInfo(BaseModel):
    id: str
    name: str
    status: str
    progress: int
    current: int
    total: int
    message: str
    error: str | None = None
    result: dict | None = None
    created_at: str
    updated_at: str


class RebuildRequest(BaseModel):
    """不填 file_path 则全量重建。"""
    file_path: str | None = None