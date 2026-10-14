"""混合检索：向量 + BM25，使用 Reciprocal Rank Fusion (RRF) 融合。"""
from langchain_core.documents import Document

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.retrievers.bm25_retriever import bm25_search
from app.rag.retrievers.vector_retriever import vector_search


logger = get_logger(__name__)


def _rrf_fuse(
    result_lists: list[list[Document]],
    *,
    rrf_k: int,
    top_k: int,
) -> list[Document]:
    """RRF 融合多路检索结果。

    score(d) = Σ 1 / (rrf_k + rank_i(d))
    rank_i 从 1 开始计。
    """
    scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    for results in result_lists:
        for rank, doc in enumerate(results, start=1):
            key = doc.metadata.get("chunk_id") or doc.page_content[:64]
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            doc_map.setdefault(key, doc)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    fused: list[Document] = []
    for key, score in ranked:
        d = doc_map[key]
        d.metadata["rrf_score"] = round(score, 6)
        fused.append(d)
    return fused


def hybrid_search(
    query: str,
    *,
    vector_k: int | None = None,
    bm25_k: int | None = None,
    top_k: int | None = None,
) -> list[Document]:
    """向量 + BM25 混合检索，RRF 融合。"""
    s = get_settings()
    vector_k = vector_k or s.vector_top_k
    bm25_k = bm25_k or s.bm25_top_k
    top_k = top_k or s.hybrid_top_k

    vec_hits = vector_search(query, k=vector_k)
    bm_hits = bm25_search(query, k=bm25_k)
    fused = _rrf_fuse([vec_hits, bm_hits], rrf_k=s.rrf_k, top_k=top_k)

    logger.info(
        "混合检索 | vec=%d bm25=%d → fused=%d | query=%s",
        len(vec_hits), len(bm_hits), len(fused), query[:40],
    )
    return fused