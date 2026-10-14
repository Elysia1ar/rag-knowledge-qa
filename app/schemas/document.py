"""文档相关。"""
from pydantic import BaseModel


class DocumentItem(BaseModel):
    id: int
    file_name: str
    file_size: int
    chunk_count: int
    created_at: str


class UploadResponse(BaseModel):
    document_id: int
    file_name: str
    chunk_count: int
    skipped: bool = False