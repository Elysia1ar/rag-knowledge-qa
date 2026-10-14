"""Golden Set 加载。"""
import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


@dataclass
class GoldenItem:
    question: str
    ground_truth: str


def load_golden_set(path: Path | None = None) -> list[GoldenItem]:
    settings = get_settings()
    path = path or (settings.eval_dir / "golden_set.jsonl")

    if not path.exists():
        raise FileNotFoundError(f"Golden Set 不存在：{path}")

    items: list[GoldenItem] = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                items.append(GoldenItem(
                    question=obj["question"],
                    ground_truth=obj["ground_truth"],
                ))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("第 %d 行解析失败：%s", line_no, e)

    logger.info("加载 Golden Set：%d 条", len(items))
    return items