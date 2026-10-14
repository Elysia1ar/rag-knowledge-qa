"""生成层冒烟测试：跑通完整 RAG 问答。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.rag.pipeline.query_pipeline import run_query


QUESTIONS = [
    "RAG 的典型管线包括哪些步骤？",
    "为什么 RAG 能减少大模型的幻觉？",
    "Bi-Encoder 和 Cross-Encoder 有什么区别？",
    "Chroma 和 Milvus 分别适合什么场景？",
    "我想问一个知识库里没有的问题：今天天气怎么样？",  # 测试防幻觉
]


def main() -> None:
    setup_logging()
    for q in QUESTIONS:
        print(f"\n{'=' * 70}\n❓ {q}\n{'=' * 70}")
        result = run_query(q)
        print(f"\n💡 {result.answer}\n")
        print("📚 引用来源：")
        for s in result.sources:
            print(f"   [{s['index']}] {s['file_name']}  "
                  f"(rerank={s.get('rerank_score')})")
            print(f"       {s['preview']}...")


if __name__ == "__main__":
    main()