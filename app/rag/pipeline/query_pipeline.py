"""查询管线：改写 → 检索 → 重排 → 生成。"""
from dataclasses import dataclass, field
#查询管线
from app.core.logging import get_logger
from app.rag.chains.condense_chain import condense_question
from app.rag.chains.qa_chain import QAResult, answer_question


logger = get_logger(__name__)


@dataclass
class QueryResult:
    question: str                  # 原始问题
    rewritten_question: str        # 改写后的问题
    answer: str
    sources: list[dict] = field(default_factory=list)
    memory_count: int = 0          # ← 新增

def run_query(
    question: str,
    chat_history: list[dict] | None = None,
    top_k: int | None = None,
    memory_block: str = "",
) -> QueryResult:
    rewritten = condense_question(question, chat_history)
    result: QAResult = answer_question(
        rewritten, top_k=top_k, memory_block=memory_block,
    )

    return QueryResult(
        question=question,
        rewritten_question=rewritten,
        answer=result.answer,
        sources=result.sources,
    )