"""会话与消息表。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="新会话")

    # ---- 短期记忆 ----
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="摘要已覆盖会话内前 N 条消息",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
        onupdate=func.now(), nullable=False)

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="session",
        cascade="all, delete-orphan", order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False)

    session: Mapped[Session] = relationship("Session", back_populates="messages")