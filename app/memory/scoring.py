"""记忆综合评分。

参考 Generative Agents 的记忆流 + Hello-Agents 的三因素评分：
  score = (w1×相关性 + w2×时间近因性 + w3×重要性) × 频率加成
"""
import math
from datetime import datetime


def memory_score(
    vector_sim: float,
    created_at: datetime,
    importance: float,
    access_count: int = 0,
    *,
    now: datetime | None = None,
    tau_days: float = 30.0,
    w_relevance: float = 0.75,      # ← 0.6 → 0.75，让语义相关性主导
    w_recency: float = 0.15,        # ← 0.2 → 0.15
    w_importance: float = 0.10,     # ← 0.2 → 0.10
) -> float:
    """综合评分。

    Args:
        vector_sim: 向量相似度（0~1）
        created_at: 记忆创建时间
        importance: 重要性（0~1）
        access_count: 被访问次数
        tau_days: 时间衰减常数，越大衰减越慢
    """
    if now is None:
        now = datetime.now()

    days = max(0.0, (now - created_at).total_seconds() / 86400)
    recency = math.exp(-days / tau_days)

    frequency = 1.0 + math.log(1 + access_count) * 0.1

    raw = (
        w_relevance * vector_sim
        + w_recency * recency
        + w_importance * importance
    ) * frequency

    return min(1.0, max(0.0, raw))