"""消融实验入口。

用法：
    python -m scripts.run_eval                # 全量 20 条，三种配置
    python -m scripts.run_eval --limit 5      # 快速验证，只跑 5 条
    python -m scripts.run_eval --config +rerank   # 只跑一种
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.rag.evaluation.dataset import load_golden_set
from app.rag.evaluation.ragas_eval import RETRIEVERS, run_one_config
from app.rag.evaluation.report import print_summary, save_json


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 条")
    parser.add_argument("--config", type=str, default=None,
                        choices=list(RETRIEVERS.keys()), help="只跑一种配置")
    args = parser.parse_args()

    items = load_golden_set()
    configs = [args.config] if args.config else list(RETRIEVERS.keys())

    results = []
    for cfg in configs:
        print(f"\n{'#' * 70}\n# 开始评估配置：{cfg}\n{'#' * 70}")
        results.append(run_one_config(cfg, items, limit=args.limit))

    print_summary(results)
    save_json(results)


if __name__ == "__main__":
    main()