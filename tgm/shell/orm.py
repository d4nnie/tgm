from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserProfileRow(Base):
    __tablename__ = "user_profile"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str | None]


class ChatRow(Base):
    __tablename__ = "chats"

    chat_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    chat_type: Mapped[str] = mapped_column("type")
    is_monitored: Mapped[bool] = mapped_column(default=False)
    period_n_minutes: Mapped[int] = mapped_column(default=30)
    added_at: Mapped[datetime]


class ChatProfileRow(Base):
    __tablename__ = "chat_profiles"

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.chat_id"), primary_key=True)
    description_prompt: Mapped[str] = mapped_column(default="")
    rolling_summary: Mapped[str] = mapped_column(default="")
    updated_at: Mapped[datetime]


class MessageRow(Base):
    __tablename__ = "messages"

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.chat_id"), primary_key=True)
    message_id: Mapped[int] = mapped_column("msg_id", primary_key=True)
    timestamp: Mapped[datetime] = mapped_column("ts")
    sender_id: Mapped[int | None]
    sender_name: Mapped[str | None]
    text: Mapped[str | None]
    reply_to_message_id: Mapped[int | None] = mapped_column("reply_to_msg_id")
    edited_at: Mapped[datetime | None]
    raw_json: Mapped[str]

    __table_args__ = (Index("idx_messages_chat_ts", "chat_id", "ts"),)


class DigestRow(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope: Mapped[str]
    chat_id: Mapped[int | None]
    run_timestamp: Mapped[datetime] = mapped_column("run_ts")
    summary: Mapped[str]
    highlights_json: Mapped[str]
    seen: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (Index("idx_digests_scope_chat_ts", "scope", "chat_id", "run_ts"),)


class ImportanceCriterionRow(Base):
    __tablename__ = "importance_criteria"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope: Mapped[str]
    criteria_text: Mapped[str]
    version: Mapped[int]
    updated_at: Mapped[datetime]

    __table_args__ = (UniqueConstraint("scope", "version"),)


class FeedbackRow(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.chat_id"))
    message_ids_json: Mapped[str] = mapped_column("msg_ids_json")
    user_comment: Mapped[str | None]
    scope: Mapped[str]
    consumed: Mapped[bool] = mapped_column(default=False)
    marked_at: Mapped[datetime]

    __table_args__ = (Index("idx_feedback_scope_consumed_marked", "scope", "consumed", "marked_at"),)


class RunStateRow(Base):
    __tablename__ = "run_state"

    scope: Mapped[str] = mapped_column(primary_key=True)
    last_run_at: Mapped[datetime | None]
    last_message_id: Mapped[int | None] = mapped_column("last_msg_id")
