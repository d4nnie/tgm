from datetime import UTC, datetime, timedelta

from tgm.core.scheduling import is_chat_due, merge_summary_parts, pick_chats_due
from tgm.core.types import Chat


def _chat(chat_id: int = 1, period: int = 30, monitored: bool = True) -> Chat:
    return Chat(
        chat_id=chat_id,
        title=f"chat-{chat_id}",
        chat_type="user",
        is_monitored=monitored,
        period_n_minutes=period,
        added_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


_NOW = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)


def test_is_chat_due_returns_true_when_no_previous_run():
    assert is_chat_due(_chat(), _NOW, last_run_at=None) is True


def test_is_chat_due_returns_true_at_exact_boundary():
    last_run = _NOW - timedelta(minutes=30)

    assert is_chat_due(_chat(period=30), _NOW, last_run) is True


def test_is_chat_due_returns_false_just_before_boundary():
    last_run = _NOW - timedelta(minutes=30) + timedelta(seconds=1)

    assert is_chat_due(_chat(period=30), _NOW, last_run) is False


def test_is_chat_due_returns_true_well_past_boundary():
    last_run = _NOW - timedelta(hours=2)

    assert is_chat_due(_chat(period=30), _NOW, last_run) is True


def test_is_chat_due_returns_false_when_now_before_last_run():
    last_run = _NOW + timedelta(minutes=5)

    assert is_chat_due(_chat(period=30), _NOW, last_run) is False


def test_pick_chats_due_returns_only_due_chats():
    chat_due = _chat(chat_id=1, period=30)
    chat_not_due = _chat(chat_id=2, period=30)

    last_run_by_chat = {
        1: _NOW - timedelta(minutes=45),
        2: _NOW - timedelta(minutes=10),
    }

    result = pick_chats_due([chat_due, chat_not_due], _NOW, last_run_by_chat)

    assert result == [chat_due]


def test_pick_chats_due_skips_unmonitored_chats():
    chat_unmonitored = _chat(chat_id=1, monitored=False)

    result = pick_chats_due([chat_unmonitored], _NOW, last_run_by_chat={})

    assert result == []


def test_pick_chats_due_handles_chat_with_no_run_state():
    chat = _chat(chat_id=1)

    result = pick_chats_due([chat], _NOW, last_run_by_chat={})

    assert result == [chat]


def test_merge_summary_parts_joins_with_blank_line():
    assert merge_summary_parts(["A", "B", "C"]) == "A\n\nB\n\nC"


def test_merge_summary_parts_drops_empty_strings():
    assert merge_summary_parts(["A", "", "B"]) == "A\n\nB"


def test_merge_summary_parts_returns_empty_for_empty_input():
    assert merge_summary_parts([]) == ""
