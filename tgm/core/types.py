from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ChatType = Literal["user", "group", "supergroup", "channel"]


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
    msg_id: int
    timestamp: datetime
    sender_id: int | None
    sender_name: str | None
    text: str | None
    reply_to_msg_id: int | None
    edited_at: datetime | None
    raw_json: str


@dataclass(frozen=True)
class RunState:
    scope: str
    last_run_at: datetime | None
    last_msg_id: int | None


@dataclass(frozen=True)
class ChatDialog:
    chat_id: int
    title: str
    chat_type: ChatType
