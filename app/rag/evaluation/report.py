"""评估报告：三种配置对比 + 逐条明细。"""
import json
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.evaluation.ragas_eval import EvalResult


logger = get_logger(__name__)


_METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def print_summary(results: list[EvalResult]) -> None:
    """打印对比表。"""
    header = f"{'Config':<12}" + "".join(f"{m:>22}" for m in _METRICS)
    print("\n" + "=" * len(header))
    print("RAGAS 消融实验对比")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for r in results:
        row = f"{r.config:<12}"
        for m in _METRICS:
            v = r.scores.get(m, float("nan"))
            row += f"{v:>22.4f}"
        print(row)

    print("=" * len(header) + "\n")


def save_json(results: list[EvalResult], path: Path | None = None) -> Path:
    """保存完整结果到 JSON。"""
    settings = get_settings()
    path = path or (settings.eval_dir / "results" / "ablation.json")
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = [
        {
            "config": r.config,
            "scores": r.scores,
            "samples": [
                {
                    "question": s.question,
                    "answer": s.answer,
                    "ground_truth": s.ground_truth,
                    "contexts": s.contexts,
                }
                for s in r.samples
            ],
        }
        for r in results
    ]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info("结果已保存：%s", path)
    return path