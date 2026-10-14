"""检索层冒烟测试：对比向量 / BM25 / 混合 / 重排。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.rag.retrievers import (
    bm25_search,
    hybrid_search,
    rerank,
    vector_search,
)


def show(title: str, docs) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")
    for i, d in enumerate(docs, 1):
        cid = d.metadata.get("chunk_id", "")[:8]
        rrf = d.metadata.get("rrf_score")
        rrk = d.metadata.get("rerank_score")
        parts = []
        if rrf is not None:
            parts.append(f"rrf={rrf:.4f}")
        if rrk is not None:
            parts.append(f"rerank={rrk:.4f}")
        score_str = " | ".join(parts) if parts else "-"
        print(f"[{i}] id={cid} {score_str}")
        print(f"    {d.page_content[:100].replace(chr(10), ' ')}...")

def main() -> None:
    setup_logging()
    query = "RAG 的典型管线包括哪些步骤？"

    vec = vector_search(query, k=5)
    show("① 向量检索 Top-5", vec)

    bm = bm25_search(query, k=5)
    show("② BM25 检索 Top-5", bm)

    fused = hybrid_search(query, top_k=10)
    show("③ 混合检索 RRF Top-10", fused)

    reranked = rerank(query, fused, top_k=5)
    show("④ 重排序后 Top-5", reranked)


if __name__ == "__main__":
    main()