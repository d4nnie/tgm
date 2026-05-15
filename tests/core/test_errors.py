import pytest

from tgm.core.errors import (
    FloodWaitOutcome,
    FloodWaitTooLongError,
    FloodWaitTooLongOutcome,
    NetworkError,
    NetworkRetryOutcome,
    RaiseFloodWaitTooLongAction,
    RaiseNetworkAction,
    RaiseSessionExpiredAction,
    ReraiseAction,
    RetrySleepAction,
    SessionExpiredError,
    SessionExpiredOutcome,
    SingleInstanceError,
    classify_telethon_error,
    decide_retry_action,
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


@pytest.mark.parametrize("attempt,expected_seconds", [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16), (5, 30)])
def test_classify_network_error_uses_exponential_backoff(attempt: int, expected_seconds: int):
    outcome = classify_telethon_error(ConnectionError("disconnected"), attempt=attempt)

    assert outcome == NetworkRetryOutcome(wait_seconds=expected_seconds, attempt=attempt)


def test_classify_network_error_returns_none_at_max_attempts():
    assert classify_telethon_error(ConnectionError(), attempt=6) is None


def test_classify_handles_os_error():
    assert classify_telethon_error(OSError(), attempt=0) == NetworkRetryOutcome(wait_seconds=1, attempt=0)


def test_classify_handles_timeout_error():
    assert classify_telethon_error(TimeoutError(), attempt=1) == NetworkRetryOutcome(wait_seconds=2, attempt=1)


def test_classify_unknown_error_returns_none():
    assert classify_telethon_error(ValueError("nope"), attempt=0) is None


def test_session_expired_error_is_runtime_error():
    assert issubclass(SessionExpiredError, RuntimeError)


def test_network_error_is_runtime_error():
    assert issubclass(NetworkError, RuntimeError)


def test_decide_retry_action_sleeps_for_flood_wait():
    action = decide_retry_action(_FakeFloodWaitError(seconds=30), attempt=0)

    assert action == RetrySleepAction(seconds=30, message="Throttled by Telegram, retry in 30s")


def test_decide_retry_action_sleeps_for_network_retry():
    action = decide_retry_action(ConnectionError("flap"), attempt=2)

    assert action == RetrySleepAction(seconds=4, message="Network error, retry in 4s (attempt 3/6)")


def test_decide_retry_action_raises_session_expired_for_auth_key():
    assert decide_retry_action(_FakeAuthKeyError(), attempt=0) == RaiseSessionExpiredAction()


def test_decide_retry_action_raises_network_after_attempts_exhausted():
    assert decide_retry_action(ConnectionError(), attempt=6) == RaiseNetworkAction()


def test_decide_retry_action_reraises_unknown_error():
    assert decide_retry_action(ValueError("boom"), attempt=0) == ReraiseAction()


class _FakeAuthKeyDuplicatedError(Exception):
    pass


_FakeAuthKeyDuplicatedError.__name__ = "AuthKeyDuplicatedError"


class _FakeUserDeactivatedBanError(Exception):
    pass


_FakeUserDeactivatedBanError.__name__ = "UserDeactivatedBanError"


def test_classify_auth_key_duplicated_returns_session_expired():
    assert classify_telethon_error(_FakeAuthKeyDuplicatedError(), attempt=0) == SessionExpiredOutcome()


def test_classify_user_deactivated_ban_returns_session_expired():
    assert classify_telethon_error(_FakeUserDeactivatedBanError(), attempt=0) == SessionExpiredOutcome()


@pytest.mark.parametrize("error_name", ["ServerError", "RpcCallFailError", "RpcMcgetFailError"])
def test_classify_telethon_server_error_returns_network_retry(error_name: str):
    class _FakeError(Exception):
        pass

    _FakeError.__name__ = error_name

    outcome = classify_telethon_error(_FakeError(), attempt=0)

    assert isinstance(outcome, NetworkRetryOutcome)


def test_classify_server_error_exhausted_returns_none():
    class _FakeError(Exception):
        pass

    _FakeError.__name__ = "ServerError"

    assert classify_telethon_error(_FakeError(), attempt=6) is None


def test_decide_retry_action_sleeps_for_server_error():
    class _FakeError(Exception):
        pass

    _FakeError.__name__ = "ServerError"

    action = decide_retry_action(_FakeError(), attempt=1)

    assert action == RetrySleepAction(seconds=2, message="Network error, retry in 2s (attempt 2/6)")


def test_decide_retry_action_raises_network_for_exhausted_server_error():
    class _FakeError(Exception):
        pass

    _FakeError.__name__ = "ServerError"

    assert decide_retry_action(_FakeError(), attempt=6) == RaiseNetworkAction()


def test_classify_flood_wait_under_cap_returns_retryable_outcome():
    outcome = classify_telethon_error(_FakeFloodWaitError(seconds=600), attempt=0)

    assert outcome == FloodWaitOutcome(wait_seconds=600)


def test_classify_flood_wait_over_cap_returns_too_long_outcome():
    outcome = classify_telethon_error(_FakeFloodWaitError(seconds=601), attempt=0)

    assert outcome == FloodWaitTooLongOutcome(wait_seconds=601)


def test_classify_flood_wait_day_returns_too_long_outcome():
    outcome = classify_telethon_error(_FakeFloodWaitError(seconds=86400), attempt=0)

    assert outcome == FloodWaitTooLongOutcome(wait_seconds=86400)


def test_decide_retry_action_long_flood_raises():
    action = decide_retry_action(_FakeFloodWaitError(seconds=86400), attempt=0)

    assert action == RaiseFloodWaitTooLongAction(wait_seconds=86400)


def test_flood_wait_too_long_error_is_runtime_error():
    assert issubclass(FloodWaitTooLongError, RuntimeError)


def test_single_instance_error_is_runtime_error():
    assert issubclass(SingleInstanceError, RuntimeError)
