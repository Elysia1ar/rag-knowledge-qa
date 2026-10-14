"""BM25 关键词检索：从 Chroma 拉全文，构建/缓存倒排索引。"""
import pickle
from pathlib import Path

import jieba
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.vectorstore import count, get_vectorstore


logger = get_logger(__name__)


def _tokenize(text: str) -> list[str]:
    """中文分词 + 小写化，过滤空白 token。"""
    return [t for t in jieba.lcut_for_search(text.lower()) if t.strip()]


def _load_all_documents() -> list[Document]:
    """从 Chroma 拉全部 chunk（文本 + 元数据）。"""
    vs = get_vectorstore()
    data = vs.get(include=["documents", "metadatas"])
    docs: list[Document] = []
    for content, meta in zip(data["documents"], data["metadatas"]):
        docs.append(Document(page_content=content, metadata=meta or {}))
    return docs


def _build_index() -> tuple[BM25Okapi, list[Document]]:
    docs = _load_all_documents()
    if not docs:
        raise RuntimeError("Chroma 中暂无文档，请先运行 python -m scripts.ingest")

    corpus_tokens = [_tokenize(d.page_content) for d in docs]
    bm25 = BM25Okapi(corpus_tokens)
    return bm25, docs


def build_and_cache() -> int:
    """构建 BM25 索引并落盘，返回文档数。"""
    settings = get_settings()
    bm25, docs = _build_index()
    payload = {
        "docs": [(d.page_content, d.metadata) for d in docs],
        "bm25": bm25,
    }
    with open(settings.bm25_cache, "wb") as f:
        pickle.dump(payload, f)
    logger.info("BM25 索引已缓存：%d 篇 → %s", len(docs), settings.bm25_cache)
    return len(docs)


def _load_or_build() -> tuple[BM25Okapi, list[Document]]:
    settings = get_settings()
    if settings.bm25_cache.exists():
        try:
            with open(settings.bm25_cache, "rb") as f:
                payload = pickle.load(f)
            docs = [Document(page_content=c, metadata=m)
                    for c, m in payload["docs"]]
            return payload["bm25"], docs
        except Exception as e:
            logger.warning("BM25 缓存损坏，重建中：%s", e)

    bm25, docs = _build_index()
    payload = {"docs": [(d.page_content, d.metadata) for d in docs], "bm25": bm25}
    with open(settings.bm25_cache, "wb") as f:
        pickle.dump(payload, f)
    return bm25, docs


def invalidate_cache() -> None:
    """文档库变更后调用，强制下次重建。"""
    p = get_settings().bm25_cache
    if p.exists():
        p.unlink()
        logger.info("BM25 缓存已失效：%s", p)


def bm25_search(query: str, k: int = 20) -> list[Document]:
    """按 BM25 打分返回 Top-K。"""
    bm25, docs = _load_or_build()
    scores = bm25.get_scores(_tokenize(query))
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    hits = [docs[i] for i in order if scores[i] > 0]
    logger.debug("BM25 检索命中 %d 条 | query=%s", len(hits), query[:40])
    return hits