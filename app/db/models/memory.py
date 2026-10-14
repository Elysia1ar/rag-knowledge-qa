"""长期记忆表。

一条 Memory 代表一个值得长期记住的信息片段，通常是：
  - 用户的事实（职业、项目、技能）
  - 用户的偏好（回答风格、关注领域）
  - 历史结论（之前讨论过什么、达成什么共识）

与 Message 的区别：
  Message  是原始的对话流水
  Memory   是从对话中提炼出的、跨会话可用的结构化信息
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )

    # ---- 内容 ----
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="fact",
        comment="fact | preference | conclusion | event",
    )

    # ---- 评分维度（C3.4 / C3.5 用）----
    importance: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
        comment="0~1，由 LLM 打分，驱动遗忘与固化",
    )
    access_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
    )

    # ---- 溯源 ----
    source_session_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
    )
    source_question: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- 时间戳 ----
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
        onupdate=func.now(), nullable=False)