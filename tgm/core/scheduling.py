from datetime import datetime, timedelta

from tgm.core.types import Chat


def is_chat_due(chat: Chat, now: datetime, last_run_at: datetime | None) -> bool:
    if last_run_at is None:
        return True
    if now < last_run_at:
        return False
    return now - last_run_at >= timedelta(minutes=chat.period_n_minutes)


def pick_chats_due(
    chats: list[Chat],
    now: datetime,
    last_run_by_chat: dict[int, datetime],
) -> list[Chat]:
    return [chat for chat in chats if chat.is_monitored and is_chat_due(chat, now, last_run_by_chat.get(chat.chat_id))]


def merge_summary_parts(parts: list[str]) -> str:
    return "\n\n".join(part for part in parts if part)
