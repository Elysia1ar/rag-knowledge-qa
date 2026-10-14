"""向量检索：直接封装 Chroma 的相似度搜索。"""
from langchain_core.documents import Document

from app.core.logging import get_logger
from app.rag.vectorstore import get_vectorstore


logger = get_logger(__name__)


def vector_search(query: str, k: int = 20) -> list[Document]:
    """返回与 query 语义最相似的 k 个 chunk。"""
    vs = get_vectorstore()
    docs = vs.similarity_search(query, k=k)
    logger.debug("向量检索命中 %d 条 | query=%s", len(docs), query[:40])
    return docs