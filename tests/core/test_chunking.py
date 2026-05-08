from datetime import UTC, datetime

from tgm.core.chunking import split_into_chunks, trim_to_budget
from tgm.core.types import Message, PerChatDigestPart, PerChatHighlightPart


def _message(message_id: int, text: str = "msg") -> Message:
    return Message(
        chat_id=1,
        message_id=message_id,
        timestamp=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
        sender_id=1,
        sender_name="Alice",
        text=text,
        reply_to_message_id=None,
        edited_at=None,
        raw_json="{}",
    )


def test_split_into_chunks_returns_empty_for_no_messages():
    assert split_into_chunks([], max_messages_per_chunk=10, max_tokens_per_chunk=1000) == []


def test_split_into_chunks_splits_by_message_count():
    messages = [_message(index) for index in range(5)]

    chunks = split_into_chunks(messages, max_messages_per_chunk=2, max_tokens_per_chunk=10_000)

    assert [len(chunk) for chunk in chunks] == [2, 2, 1]


def test_split_into_chunks_preserves_message_ids_in_order():
    messages = [_message(index) for index in range(7)]

    chunks = split_into_chunks(messages, max_messages_per_chunk=3, max_tokens_per_chunk=10_000)

    flattened = [message.message_id for chunk in chunks for message in chunk]
    assert flattened == list(range(7))


def test_split_into_chunks_splits_by_token_budget():
    big_text = "a" * 300
    messages = [_message(index, text=big_text) for index in range(4)]

    chunks = split_into_chunks(messages, max_messages_per_chunk=100, max_tokens_per_chunk=120)

    assert len(chunks) > 1
    flattened_ids = [message.message_id for chunk in chunks for message in chunk]
    assert flattened_ids == [0, 1, 2, 3]


def test_split_into_chunks_keeps_oversized_message_alone():
    huge_text = "a" * 5000
    messages = [_message(0, text=huge_text), _message(1, text="small")]

    chunks = split_into_chunks(messages, max_messages_per_chunk=10, max_tokens_per_chunk=50)

    assert chunks[0] == [messages[0]]
    assert chunks[1] == [messages[1]]


def _digest_part(chat_id: int, summary: str, highlight_count: int) -> PerChatDigestPart:
    return PerChatDigestPart(
        chat_id=chat_id,
        title=f"chat-{chat_id}",
        summary=summary,
        highlights=[PerChatHighlightPart(message_id=index, why="x" * 30) for index in range(highlight_count)],
    )


def test_trim_to_budget_returns_input_unchanged_when_within_budget():
    parts = [_digest_part(1, summary="short", highlight_count=2)]

    result = trim_to_budget(parts, max_tokens=10_000)

    assert result == parts


def test_trim_to_budget_strips_oldest_highlights_first():
    parts = [
        _digest_part(1, summary="short", highlight_count=20),
        _digest_part(2, summary="short", highlight_count=20),
    ]

    result = trim_to_budget(parts, max_tokens=80)

    assert result[0].highlights == []
    assert len(result[1].highlights) == 20


def test_trim_to_budget_preserves_newest_highlights_even_when_over_budget():
    parts = [
        _digest_part(1, summary="long " * 100, highlight_count=10),
        _digest_part(2, summary="long " * 100, highlight_count=10),
    ]

    result = trim_to_budget(parts, max_tokens=10)

    assert result[0].highlights == []
    assert len(result[1].highlights) == 10


def test_trim_to_budget_keeps_lone_part_highlights_intact():
    parts = [_digest_part(1, summary="kept", highlight_count=10)]

    result = trim_to_budget(parts, max_tokens=1)

    assert result[0].summary == "kept"
    assert len(result[0].highlights) == 10
