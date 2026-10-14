"""Cross-Encoder 重排序，使用 BGE-Reranker。"""
import os
from functools import lru_cache

from langchain_core.documents import Document

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


@lru_cache
def _get_reranker():
    """惰性加载 CrossEncoder，同时确保 HF 镜像环境已设置。"""
    s = get_settings()
    os.environ.setdefault("HF_ENDPOINT", s.hf_endpoint)
    os.environ.setdefault("HF_HOME", str(s.hf_home))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    from sentence_transformers import CrossEncoder

    logger.info("加载 Reranker: %s (%s)", s.reranker_model, s.embedding_device)
    return CrossEncoder(s.reranker_model, device=s.embedding_device)


def rerank(query: str, docs: list[Document], top_k: int = 5) -> list[Document]:
    """对候选文档按 query 相关性重新打分并截断。"""
    if not docs:
        return []

    s = get_settings()
    if not s.reranker_enabled:
        return docs[:top_k]

    model = _get_reranker()
    pairs = [(query, d.page_content) for d in docs]
    scores = model.predict(pairs, batch_size=16, show_progress_bar=False)

    ranked = sorted(zip(docs, scores), key=lambda x: float(x[1]), reverse=True)
    results: list[Document] = []
    for doc, score in ranked[:top_k]:
        doc.metadata["rerank_score"] = round(float(score), 6)
        results.append(doc)

    logger.info("重排序 %d → %d", len(docs), len(results))
    return results