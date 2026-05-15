from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

ChatType = Literal["user", "group", "supergroup", "channel"]
LlmProvider = Literal["openai-compat"]
StatusCallback = Callable[[str], None]


@dataclass(frozen=True)
class TelegramCredentials:
    api_id: int
    api_hash: str
    phone: str | None = None


@dataclass(frozen=True)
class Chat:
    chat_id: int
    title: str
    chat_type: ChatType
    is_monitored: bool
    period_n_minutes: int
    added_at: datetime


@dataclass(frozen=True)
class Message:
    chat_id: int
    message_id: int
    timestamp: datetime
    sender_id: int | None
    sender_name: str | None
    text: str | None
    reply_to_message_id: int | None
    edited_at: datetime | None
    raw_json: str


@dataclass(frozen=True)
class RunState:
    scope: str
    last_run_at: datetime | None
    last_message_id: int | None


@dataclass(frozen=True)
class ChatDialog:
    chat_id: int
    title: str
    chat_type: ChatType


@dataclass(frozen=True)
class ChatProfile:
    chat_id: int
    description_prompt: str
    rolling_summary: str
    updated_at: datetime


@dataclass(frozen=True)
class ImportanceCriteria:
    id: int
    scope: str
    criteria_text: str
    version: int
    updated_at: datetime


@dataclass(frozen=True)
class Feedback:
    id: int
    chat_id: int
    message_ids: list[int]
    user_comment: str | None
    scope: Literal["chat", "global"]
    consumed: bool
    marked_at: datetime


@dataclass(frozen=True)
class LlmProviderConfig:
    provider: LlmProvider
    base_url: str
    model: str
    api_key_env: str | None = None
    options: dict[str, Any] | None = None
    allow_hosts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PerChatHighlightPart:
    message_id: int
    why: str


@dataclass(frozen=True)
class PerChatDigestPart:
    chat_id: int
    title: str
    summary: str
    highlights: list[PerChatHighlightPart]


@dataclass(frozen=True)
class FeedbackSample:
    user_comment: str | None
    messages: list[Message]
