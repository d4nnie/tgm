from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

ChatType = Literal["user", "group", "supergroup", "channel"]
LlmProvider = Literal["openai-compat", "anthropic"]

_FROZEN_STRICT = ConfigDict(frozen=True, extra="forbid")


class TelegramCredentials(BaseModel):
    model_config = _FROZEN_STRICT

    api_id: int
    api_hash: str
    phone: str | None = None


class Chat(BaseModel):
    model_config = _FROZEN_STRICT

    chat_id: int
    title: str
    chat_type: ChatType
    is_monitored: bool
    period_n_minutes: int
    added_at: datetime


class Message(BaseModel):
    model_config = _FROZEN_STRICT

    chat_id: int
    message_id: int
    timestamp: datetime
    sender_id: int | None
    sender_name: str | None
    text: str | None
    reply_to_message_id: int | None
    edited_at: datetime | None
    raw_json: str


class RunState(BaseModel):
    model_config = _FROZEN_STRICT

    scope: str
    last_run_at: datetime | None
    last_message_id: int | None


class ChatDialog(BaseModel):
    model_config = _FROZEN_STRICT

    chat_id: int
    title: str
    chat_type: ChatType


class LlmProviderConfig(BaseModel):
    model_config = _FROZEN_STRICT

    provider: LlmProvider
    base_url: str
    model: str
    api_key_env: str | None = None
    options: dict[str, Any] | None = None
