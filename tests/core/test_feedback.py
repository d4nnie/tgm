from datetime import UTC, datetime

from tgm.core.feedback import build_feedback_samples, group_feedback_by_chat
from tgm.core.types import Feedback, Message


def _message(chat_id: int, message_id: int) -> Message:
    return Message(
        chat_id=chat_id,
        message_id=message_id,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        sender_id=None,
        sender_name=None,
        text=f"msg{message_id}",
        reply_to_message_id=None,
        edited_at=None,
        raw_json="{}",
    )


def _feedback(feedback_id: int, chat_id: int, message_ids: list[int]) -> Feedback:
    return Feedback(
        id=feedback_id,
        chat_id=chat_id,
        message_ids=message_ids,
        user_comment=None,
        scope="chat",
        consumed=False,
        marked_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_group_feedback_by_chat_buckets_by_chat_id():
    items = [_feedback(1, 100, [1]), _feedback(2, 200, [2]), _feedback(3, 100, [3])]

    grouped = group_feedback_by_chat(items)

    assert set(grouped.keys()) == {100, 200}
    assert [f.id for f in grouped[100]] == [1, 3]
    assert [f.id for f in grouped[200]] == [2]


def test_group_feedback_by_chat_empty_input_returns_empty_dict():
    assert group_feedback_by_chat([]) == {}


def test_build_feedback_samples_matches_messages_by_pair():
    feedback_items = [_feedback(1, 100, [10, 11])]
    messages_by_pair = {
        (100, 10): _message(100, 10),
        (100, 11): _message(100, 11),
    }

    samples = build_feedback_samples(feedback_items, messages_by_pair)

    assert len(samples) == 1
    assert [m.message_id for m in samples[0].messages] == [10, 11]


def test_build_feedback_samples_skips_missing_messages():
    feedback_items = [_feedback(1, 100, [10, 99])]
    messages_by_pair = {(100, 10): _message(100, 10)}

    samples = build_feedback_samples(feedback_items, messages_by_pair)

    assert [m.message_id for m in samples[0].messages] == [10]


def test_build_feedback_samples_preserves_message_id_order():
    feedback_items = [_feedback(1, 100, [10, 12, 11])]
    messages_by_pair = {
        (100, 10): _message(100, 10),
        (100, 11): _message(100, 11),
        (100, 12): _message(100, 12),
    }

    samples = build_feedback_samples(feedback_items, messages_by_pair)

    assert [m.message_id for m in samples[0].messages] == [10, 12, 11]
