"""系统状态相关 Schema。"""
from pydantic import BaseModel


class VectorStoreStats(BaseModel):
    collection: str
    total_chunks: int


class DocumentStats(BaseModel):
    total_docs: int
    total_chunks: int


class SessionStats(BaseModel):
    total_sessions: int
    total_messages: int


class SystemInfo(BaseModel):
    app_name: str
    app_env: str
    version: str
    embedding_model: str
    embedding_device: str
    reranker_enabled: bool
    reranker_model: str
    llm_provider: str
    llm_model: str
    chunk_size: int
    chunk_overlap: int


class StatsResponse(BaseModel):
    vectorstore: VectorStoreStats
    documents: DocumentStats
    sessions: SessionStats
    system: SystemInfo