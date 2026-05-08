import pytest

from tgm.core.errors import (
    FloodWaitOutcome,
    NetworkError,
    NetworkRetryOutcome,
    SessionExpiredError,
    SessionExpiredOutcome,
    classify_telethon_error,
)


class _FakeFloodWaitError(Exception):
    def __init__(self, seconds: int) -> None:
        super().__init__(f"flood wait {seconds}s")
        self.seconds = seconds


_FakeFloodWaitError.__name__ = "FloodWaitError"


class _FakeAuthKeyError(Exception):
    pass


_FakeAuthKeyError.__name__ = "AuthKeyError"


class _FakeAuthKeyUnregisteredError(Exception):
    pass


_FakeAuthKeyUnregisteredError.__name__ = "AuthKeyUnregisteredError"


class _FakeUserDeactivatedError(Exception):
    pass


_FakeUserDeactivatedError.__name__ = "UserDeactivatedError"


def test_classify_flood_wait_extracts_seconds():
    assert classify_telethon_error(_FakeFloodWaitError(seconds=42), attempt=0) == FloodWaitOutcome(wait_seconds=42)


def test_classify_flood_wait_defaults_to_zero_when_seconds_missing():
    error = _FakeFloodWaitError(seconds=0)
    delattr(error, "seconds")

    assert classify_telethon_error(error, attempt=0) == FloodWaitOutcome(wait_seconds=0)


def test_classify_auth_key_error_returns_session_expired():
    assert classify_telethon_error(_FakeAuthKeyError(), attempt=0) == SessionExpiredOutcome()


def test_classify_auth_key_unregistered_returns_session_expired():
    assert classify_telethon_error(_FakeAuthKeyUnregisteredError(), attempt=0) == SessionExpiredOutcome()


def test_classify_user_deactivated_returns_session_expired():
    assert classify_telethon_error(_FakeUserDeactivatedError(), attempt=0) == SessionExpiredOutcome()


@pytest.mark.parametrize("attempt,expected_seconds", [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16)])
def test_classify_network_error_uses_exponential_backoff(attempt: int, expected_seconds: int):
    outcome = classify_telethon_error(ConnectionError("disconnected"), attempt=attempt)

    assert outcome == NetworkRetryOutcome(wait_seconds=expected_seconds, attempt=attempt)


def test_classify_network_error_caps_backoff_at_thirty_seconds():
    outcome = classify_telethon_error(OSError("network down"), attempt=4)

    assert isinstance(outcome, NetworkRetryOutcome)
    assert outcome.wait_seconds <= 30


def test_classify_network_error_returns_none_at_max_attempts():
    assert classify_telethon_error(ConnectionError(), attempt=5) is None


def test_classify_handles_os_error():
    assert isinstance(classify_telethon_error(OSError(), attempt=0), NetworkRetryOutcome)


def test_classify_handles_timeout_error():
    assert isinstance(classify_telethon_error(TimeoutError(), attempt=1), NetworkRetryOutcome)


def test_classify_unknown_error_returns_none():
    assert classify_telethon_error(ValueError("nope"), attempt=0) is None


def test_session_expired_error_is_runtime_error():
    assert issubclass(SessionExpiredError, RuntimeError)


def test_network_error_is_runtime_error():
    assert issubclass(NetworkError, RuntimeError)
