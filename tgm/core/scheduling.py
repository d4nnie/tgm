from datetime import datetime, timedelta

from tgm.core.types import Chat


def is_chat_due(chat: Chat, now: datetime, last_run_at: datetime | None) -> bool:
    # Clock skew (future last_run_at) treated as due; one fire resets state via upsert_run_state.
    if last_run_at is None or now < last_run_at:
        return True
    return now - last_run_at >= timedelta(minutes=chat.period_n_minutes)


def pick_chats_due(
    chats: list[Chat],
    now: datetime,
    last_run_by_chat: dict[int, datetime],
) -> list[Chat]:
    def is_pickable(chat: Chat) -> bool:
        last_run_at = last_run_by_chat.get(chat.chat_id)
        return chat.is_monitored and is_chat_due(chat, now, last_run_at)

    return [chat for chat in chats if is_pickable(chat)]


def merge_summary_parts(parts: list[str]) -> str:
    return "\n\n".join(part for part in parts if part)
