"""问答相关请求与响应。"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(None, description="不传则创建新会话")
    top_k: int = Field(5, ge=1, le=20)


class SourceItem(BaseModel):
    index: int
    file_name: str
    source: str | None = None
    chunk_id: str | None = None
    preview: str
    rerank_score: float | None = None


class ChatResponse(BaseModel):
    session_id: str
    question: str
    rewritten_question: str
    answer: str
    sources: list[SourceItem] = []


class SessionDetail(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[dict] = []

class SessionItem(BaseModel):
    """会话列表项。"""
    id: str
    title: str
    message_count: int
    has_summary: bool = False              # ← 新增
    summary_message_count: int = 0         # ← 新增
    created_at: str
    updated_at: str


class SessionRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)