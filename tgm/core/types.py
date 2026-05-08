from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

ChatType = Literal["user", "group", "supergroup", "channel"]
LlmProvider = Literal["openai-compat", "anthropic"]


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
class LlmProviderConfig:
    provider: LlmProvider
    base_url: str
    model: str
    api_key_env: str | None = None
    options: dict[str, Any] | None = None
