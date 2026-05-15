from tgm.core.logging_filter import is_field_allowed


def test_is_field_allowed_for_chat_id():
    assert is_field_allowed("chat_id") is True


def test_is_field_allowed_for_latency_ms():
    assert is_field_allowed("latency_ms") is True


def test_is_field_allowed_rejects_text():
    assert is_field_allowed("text") is False


def test_is_field_allowed_rejects_sender_name():
    assert is_field_allowed("sender_name") is False


def test_is_field_allowed_rejects_raw_json():
    assert is_field_allowed("raw_json") is False


def test_is_field_allowed_rejects_prompt():
    assert is_field_allowed("prompt") is False


def test_is_field_allowed_rejects_unknown_field():
    assert is_field_allowed("user_secret") is False


def test_is_field_allowed_accepts_attempt_metrics():
    assert is_field_allowed("attempt") is True
    assert is_field_allowed("attempts") is True
    assert is_field_allowed("sleep_seconds") is True


def test_is_field_allowed_accepts_lock_metadata():
    assert is_field_allowed("lock_path") is True
    assert is_field_allowed("mutex") is True
