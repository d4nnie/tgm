from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from tgm.core.parsing import (
    MessageEditPayload,
    build_edit_payload_from_telethon,
    build_message_from_telethon,
    classify_telethon_entity,
    extract_entity_display_name,
    extract_sender_name,
    row_to_chat,
    row_to_message,
    serialize_telethon_message,
)
from tgm.core.types import Chat, Message


def test_extract_sender_name_returns_none_for_none():
    assert extract_sender_name(None) is None


def test_extract_sender_name_uses_title_when_present():
    sender = SimpleNamespace(title="Some Channel")

    assert extract_sender_name(sender) == "Some Channel"


def test_extract_sender_name_combines_first_and_last_for_user():
    sender = SimpleNamespace(first_name="Alice", last_name="Smith")

    assert extract_sender_name(sender) == "Alice Smith"


def test_extract_sender_name_handles_first_only():
    sender = SimpleNamespace(first_name="Alice", last_name=None)

    assert extract_sender_name(sender) == "Alice"


def test_extract_sender_name_handles_last_only():
    sender = SimpleNamespace(first_name=None, last_name="Smith")

    assert extract_sender_name(sender) == "Smith"


def test_extract_sender_name_falls_back_to_username():
    sender = SimpleNamespace(first_name=None, last_name=None, username="alice42")

    assert extract_sender_name(sender) == "@alice42"


def test_extract_sender_name_returns_none_when_all_fields_missing():
    assert extract_sender_name(SimpleNamespace()) is None


def test_extract_sender_name_returns_none_on_empty_strings():
    sender = SimpleNamespace(first_name="", last_name="", username="")

    assert extract_sender_name(sender) is None


def test_extract_sender_name_prefers_title_over_user_fields():
    sender = SimpleNamespace(title="Channel", first_name="Bot")

    assert extract_sender_name(sender) == "Channel"


def test_extract_sender_name_skips_empty_title():
    sender = SimpleNamespace(title="", first_name="Alice")

    assert extract_sender_name(sender) == "Alice"


def test_build_message_combines_required_fields():
    sender = SimpleNamespace(id=100, first_name="Alice")
    telethon_message = SimpleNamespace(
        id=42,
        date=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
        text="hello",
        reply_to_msg_id=None,
    )

    result = build_message_from_telethon(
        chat_id=999,
        telethon_message=telethon_message,
        sender=sender,
        raw_json="{}",
        fallback_timestamp=datetime(1970, 1, 1, tzinfo=UTC),
    )

    assert result == Message(
        chat_id=999,
        msg_id=42,
        timestamp=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
        sender_id=100,
        sender_name="Alice",
        text="hello",
        reply_to_msg_id=None,
        edited_at=None,
        raw_json="{}",
    )


def test_build_message_handles_no_sender():
    telethon_message = SimpleNamespace(id=1, date=None, text="x", reply_to_msg_id=None)
    fallback = datetime(2020, 1, 1, tzinfo=UTC)

    result = build_message_from_telethon(
        chat_id=1,
        telethon_message=telethon_message,
        sender=None,
        raw_json="{}",
        fallback_timestamp=fallback,
    )

    assert result.sender_id is None
    assert result.sender_name is None
    assert result.timestamp == fallback


def test_build_message_falls_back_when_date_missing():
    telethon_message = SimpleNamespace(id=1, date=None, text="x", reply_to_msg_id=None)
    fallback = datetime(2020, 1, 1, tzinfo=UTC)

    result = build_message_from_telethon(
        chat_id=1,
        telethon_message=telethon_message,
        sender=SimpleNamespace(id=1, first_name="A"),
        raw_json="{}",
        fallback_timestamp=fallback,
    )

    assert result.timestamp == fallback


def test_build_message_treats_empty_text_as_none():
    telethon_message = SimpleNamespace(id=1, date=datetime(2026, 1, 1, tzinfo=UTC), text="", reply_to_msg_id=None)

    result = build_message_from_telethon(
        chat_id=1,
        telethon_message=telethon_message,
        sender=SimpleNamespace(id=1, first_name="A"),
        raw_json="{}",
        fallback_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
    )

    assert result.text is None


def test_build_message_extracts_reply_to():
    telethon_message = SimpleNamespace(id=10, date=datetime(2026, 1, 1, tzinfo=UTC), text="t", reply_to_msg_id=7)

    result = build_message_from_telethon(
        chat_id=1,
        telethon_message=telethon_message,
        sender=SimpleNamespace(id=1, first_name="A"),
        raw_json="{}",
        fallback_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
    )

    assert result.reply_to_msg_id == 7


def test_build_edit_payload_uses_edit_date_when_present():
    edit_date = datetime(2026, 5, 7, 12, 30, tzinfo=UTC)
    telethon_message = SimpleNamespace(id=42, edit_date=edit_date, text="changed")

    result = build_edit_payload_from_telethon(
        chat_id=999,
        telethon_message=telethon_message,
        raw_json="{}",
        fallback_edited_at=datetime(1970, 1, 1, tzinfo=UTC),
    )

    assert result == MessageEditPayload(chat_id=999, msg_id=42, text="changed", edited_at=edit_date, raw_json="{}")


def test_build_edit_payload_falls_back_when_edit_date_missing():
    fallback = datetime(2026, 5, 7, 13, 0, tzinfo=UTC)
    telethon_message = SimpleNamespace(id=42, edit_date=None, text="changed")

    result = build_edit_payload_from_telethon(
        chat_id=999,
        telethon_message=telethon_message,
        raw_json="{}",
        fallback_edited_at=fallback,
    )

    assert result.edited_at == fallback


def test_build_edit_payload_treats_empty_text_as_none():
    telethon_message = SimpleNamespace(id=42, edit_date=datetime(2026, 1, 1, tzinfo=UTC), text="")

    result = build_edit_payload_from_telethon(
        chat_id=1,
        telethon_message=telethon_message,
        raw_json="{}",
        fallback_edited_at=datetime(2020, 1, 1, tzinfo=UTC),
    )

    assert result.text is None


def test_serialize_telethon_message_dumps_simple_payload():
    class _FakeMessage:
        def to_dict(self):
            return {"id": 42, "text": "hello"}

    result = serialize_telethon_message(_FakeMessage())

    assert result == '{"id": 42, "text": "hello"}'


def test_serialize_telethon_message_handles_non_serializable_via_str():
    class _FakeMessage:
        def to_dict(self):
            return {"date": datetime(2026, 5, 7, 12, 0, tzinfo=UTC)}

    result = serialize_telethon_message(_FakeMessage())

    assert "2026-05-07 12:00:00+00:00" in result


def test_serialize_telethon_message_preserves_unicode():
    class _FakeMessage:
        def to_dict(self):
            return {"text": "Привет"}

    result = serialize_telethon_message(_FakeMessage())

    assert "Привет" in result


def test_classify_user_entity():
    assert classify_telethon_entity(SimpleNamespace(first_name="Alice")) == "user"


def test_classify_supergroup_entity():
    assert classify_telethon_entity(SimpleNamespace(megagroup=True, title="Group")) == "supergroup"


def test_classify_broadcast_channel_entity():
    assert classify_telethon_entity(SimpleNamespace(megagroup=False, title="Channel")) == "channel"


def test_classify_group_entity():
    assert classify_telethon_entity(SimpleNamespace(title="Old Group")) == "group"


def test_classify_unknown_entity_raises():
    with pytest.raises(ValueError):
        classify_telethon_entity(SimpleNamespace())


def test_extract_entity_display_name_uses_full_name_for_user():
    entity = SimpleNamespace(id=42, first_name="Alice", last_name="Smith")

    assert extract_entity_display_name(entity) == "Alice Smith"


def test_extract_entity_display_name_uses_title_for_chat():
    entity = SimpleNamespace(id=42, title="Channel")

    assert extract_entity_display_name(entity) == "Channel"


def test_extract_entity_display_name_falls_back_to_username():
    entity = SimpleNamespace(id=42, first_name=None, username="alice42")

    assert extract_entity_display_name(entity) == "@alice42"


def test_extract_entity_display_name_falls_back_to_id():
    entity = SimpleNamespace(id=42)

    assert extract_entity_display_name(entity) == "id=42"


def test_extract_entity_display_name_uses_question_mark_when_id_missing():
    assert extract_entity_display_name(SimpleNamespace()) == "id=?"


def test_row_to_chat_maps_all_fields():
    row = SimpleNamespace(
        chat_id=42,
        title="Foo",
        chat_type="group",
        is_monitored=1,
        period_n_minutes=15,
        added_at=datetime(2026, 5, 8, tzinfo=UTC),
    )

    result = row_to_chat(row)

    assert result == Chat(
        chat_id=42,
        title="Foo",
        chat_type="group",
        is_monitored=True,
        period_n_minutes=15,
        added_at=datetime(2026, 5, 8, tzinfo=UTC),
    )


def test_row_to_chat_normalizes_truthy_int_to_bool():
    row = SimpleNamespace(
        chat_id=1, title="t", chat_type="user", is_monitored=0, period_n_minutes=30, added_at=datetime(2026, 1, 1)
    )

    assert row_to_chat(row).is_monitored is False


def test_row_to_message_maps_all_fields():
    row = SimpleNamespace(
        chat_id=42,
        msg_id=7,
        timestamp=datetime(2026, 5, 8, tzinfo=UTC),
        sender_id=100,
        sender_name="Alice",
        text="hello",
        reply_to_msg_id=None,
        edited_at=None,
        raw_json='{"id":7}',
    )

    result = row_to_message(row)

    assert result == Message(
        chat_id=42,
        msg_id=7,
        timestamp=datetime(2026, 5, 8, tzinfo=UTC),
        sender_id=100,
        sender_name="Alice",
        text="hello",
        reply_to_msg_id=None,
        edited_at=None,
        raw_json='{"id":7}',
    )


def test_row_to_message_treats_null_raw_json_as_empty_string():
    row = SimpleNamespace(
        chat_id=1,
        msg_id=1,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        sender_id=None,
        sender_name=None,
        text=None,
        reply_to_msg_id=None,
        edited_at=None,
        raw_json=None,
    )

    assert row_to_message(row).raw_json == ""
