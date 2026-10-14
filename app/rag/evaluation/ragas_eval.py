"""RAGAS 评估。

对三种检索配置（vector / hybrid / hybrid+rerank）分别计算四指标。
"""
from dataclasses import dataclass, field

from datasets import Dataset
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from app.core.logging import get_logger
from app.rag.chains.qa_chain import _format_context
from app.rag.embeddings import get_embeddings
from app.rag.evaluation.dataset import GoldenItem
from app.rag.llm import get_llm
from app.rag.retrievers import hybrid_search, rerank, vector_search


logger = get_logger(__name__)


# ---- 三种检索配置 ----

def _retrieve_baseline(question: str, top_k: int = 5):
    return vector_search(question, k=top_k)


def _retrieve_hybrid(question: str, top_k: int = 5):
    docs = hybrid_search(question, top_k=10)
    return docs[:top_k]


def _retrieve_hybrid_rerank(question: str, top_k: int = 5):
    docs = hybrid_search(question, top_k=10)
    return rerank(question, docs, top_k=top_k)


RETRIEVERS = {
    "baseline":   _retrieve_baseline,
    "+bm25":      _retrieve_hybrid,
    "+rerank":    _retrieve_hybrid_rerank,
}


@dataclass
class EvalSample:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str


@dataclass
class EvalResult:
    config: str
    scores: dict[str, float] = field(default_factory=dict)
    samples: list[EvalSample] = field(default_factory=list)


def _generate_answer(question: str, contexts) -> str:
    """对一组固定 contexts 调 LLM 生成答案（用于评估对比）。"""
    from langchain_core.output_parsers import StrOutputParser
    from app.rag.chains.prompt_templates import QA_PROMPT
    from app.core.config import get_settings

    s = get_settings()
    ctx_str, _ = _format_context(contexts, s.qa_context_max_chars)
    chain = QA_PROMPT | get_llm() | StrOutputParser()
    return chain.invoke({"context": ctx_str, "question": question}).strip()


def run_one_config(
    config_name: str,
    items: list[GoldenItem],
    *,
    top_k: int = 5,
    limit: int | None = None,
) -> EvalResult:
    """对一种检索配置跑一遍评估。"""
    retriever = RETRIEVERS[config_name]
    items = items[:limit] if limit else items

    samples: list[EvalSample] = []
    for i, item in enumerate(items, 1):
        logger.info("[%s] %d/%d | %s", config_name, i, len(items), item.question[:40])
        docs = retriever(item.question, top_k=top_k)
        contexts = [d.page_content for d in docs]

        if not contexts:
            answer = "根据现有知识库，我无法回答该问题。"
        else:
            answer = _generate_answer(item.question, docs)

        samples.append(EvalSample(
            question=item.question,
            answer=answer,
            contexts=contexts,
            ground_truth=item.ground_truth,
        ))

    data = Dataset.from_dict({
        "question":     [s.question for s in samples],
        "answer":       [s.answer for s in samples],
        "contexts":     [s.contexts for s in samples],
        "ground_truth": [s.ground_truth for s in samples],
    })

    # ---- 评估器 LLM：单独构造，temperature 调高 ----
    from langchain_openai import ChatOpenAI
    from app.core.config import get_settings
    s = get_settings()
    eval_llm = ChatOpenAI(
        model=s.llm_model,
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
        temperature=0.7,
        max_tokens=s.llm_max_tokens,
    )
    evaluator_llm = LangchainLLMWrapper(eval_llm)
    evaluator_emb = LangchainEmbeddingsWrapper(get_embeddings())

    result = evaluate(
        dataset=data,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=evaluator_llm,
        embeddings=evaluator_emb,
        raise_exceptions=False,
        show_progress=True,
    )

    # ---- 结果提取：to_pandas ----
    df = result.to_pandas()
    scores = {
        "faithfulness":      float(df["faithfulness"].mean()),
        "answer_relevancy":  float(df["answer_relevancy"].mean()),
        "context_precision": float(df["context_precision"].mean()),
        "context_recall":    float(df["context_recall"].mean()),
    }
    logger.info("[%s] 评估完成：%s", config_name, scores)

    return EvalResult(config=config_name, scores=scores, samples=samples)
