import pytest

from tgm.core.scopes import parse_chat_scope


def test_parse_chat_scope_global():
    assert parse_chat_scope("global") == ("global", None)


def test_parse_chat_scope_chat_with_id():
    assert parse_chat_scope("chat:42") == ("chat", 42)


def test_parse_chat_scope_chat_with_negative_id():
    assert parse_chat_scope("chat:-1001") == ("chat", -1001)


def test_parse_chat_scope_rejects_non_integer():
    with pytest.raises(ValueError, match="integer"):
        parse_chat_scope("chat:abc")


def test_parse_chat_scope_rejects_empty():
    with pytest.raises(ValueError, match="scope"):
        parse_chat_scope("")


def test_parse_chat_scope_rejects_empty_chat_id():
    with pytest.raises(ValueError, match="integer"):
        parse_chat_scope("chat:")


def test_parse_chat_scope_rejects_random_string():
    with pytest.raises(ValueError, match="scope"):
        parse_chat_scope("random")
