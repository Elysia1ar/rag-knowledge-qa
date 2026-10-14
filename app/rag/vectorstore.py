"""Chroma 持久化向量库封装。"""
from functools import lru_cache

from langchain_chroma import Chroma

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embeddings import get_embeddings


logger = get_logger(__name__)


@lru_cache
def get_vectorstore() -> Chroma:
    """单例 Chroma 实例，持久化到 data/chroma/。"""
    s = get_settings()
    logger.info("初始化 Chroma，collection=%s, dir=%s",
                s.chroma_collection, s.chroma_dir)
    return Chroma(
        collection_name=s.chroma_collection,
        embedding_function=get_embeddings(),
        persist_directory=str(s.chroma_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )


def add_documents(chunks, ids=None) -> list[str]:
    vs = get_vectorstore()
    return vs.add_documents(chunks, ids=ids)


def delete_by_source(source: str) -> None:
    """删除某文档的所有 chunk，用于增量重建。"""
    vs = get_vectorstore()
    vs.delete(where={"source": source})
    logger.info("已删除 source=%s 的向量", source)


def count() -> int:
    return get_vectorstore()._collection.count()

# ---- 用户长期记忆的独立 collection ----

@lru_cache
def get_memory_store() -> Chroma:
    """用户记忆的向量库。

    与 rag_knowledge 分开存储，避免：
      1. 用户个性化信息污染知识库检索
      2. 知识库更新影响记忆索引
    """
    s = get_settings()
    logger.info("初始化 Chroma (memories)，collection=user_memories")
    return Chroma(
        collection_name="user_memories",
        embedding_function=get_embeddings(),
        persist_directory=str(s.chroma_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )


def add_memories(docs, ids):
    return get_memory_store().add_documents(docs, ids=ids)


def delete_memory(memory_id: str) -> None:
    try:
        get_memory_store().delete(ids=[memory_id])
    except Exception as e:
        logger.warning("删除记忆向量失败 %s: %s", memory_id, e)
