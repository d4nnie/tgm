import json
from typing import Any

import pytest

from tgm.core.llm import (
    JsonSchema,
    LLMBudgetExceededError,
    LLMHttpRetryOutcome,
    LLMResponseError,
    LLMUnavailableError,
    build_chat_completions_request,
    check_input_budget,
    classify_http_outcome,
    parse_chat_completions_response,
)
from tgm.core.tokens import estimate_tokens

_PER_CHAT_SCHEMA: JsonSchema = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary"],
    "properties": {"summary": {"type": "string"}},
}


def test_llm_budget_exceeded_error_is_runtime_error():
    assert issubclass(LLMBudgetExceededError, RuntimeError)


def test_llm_unavailable_error_is_runtime_error():
    assert issubclass(LLMUnavailableError, RuntimeError)


def test_classify_http_outcome_transport_error_returns_retry():
    outcome = classify_http_outcome(status=None, attempt=0, retry_after=None)

    assert outcome == LLMHttpRetryOutcome(wait_seconds=1, attempt=0)


def test_classify_http_outcome_503_returns_retry():
    outcome = classify_http_outcome(status=503, attempt=1, retry_after=None)

    assert outcome == LLMHttpRetryOutcome(wait_seconds=2, attempt=1)


def test_classify_http_outcome_429_respects_retry_after():
    outcome = classify_http_outcome(status=429, attempt=0, retry_after=10)

    assert outcome == LLMHttpRetryOutcome(wait_seconds=10, attempt=0)


def test_classify_http_outcome_429_caps_retry_after_at_60s():
    outcome = classify_http_outcome(status=429, attempt=0, retry_after=600)

    assert outcome == LLMHttpRetryOutcome(wait_seconds=60, attempt=0)


def test_classify_http_outcome_429_falls_back_to_backoff_without_retry_after():
    outcome = classify_http_outcome(status=429, attempt=2, retry_after=None)

    assert outcome == LLMHttpRetryOutcome(wait_seconds=4, attempt=2)


def test_classify_http_outcome_400_fails_fast():
    assert classify_http_outcome(status=400, attempt=0, retry_after=None) is None


def test_classify_http_outcome_404_fails_fast():
    assert classify_http_outcome(status=404, attempt=0, retry_after=None) is None


def test_classify_http_outcome_returns_none_after_max_retries():
    assert classify_http_outcome(status=503, attempt=3, retry_after=None) is None


def test_json_schema_alias_accepts_plain_dict():
    schema: JsonSchema = {"type": "object"}

    assert isinstance(schema, dict)


def _build_request_with_defaults(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "system": "be helpful",
        "user": "hello",
        "schema": _PER_CHAT_SCHEMA,
        "model": "gpt-oss:20b",
    }
    defaults.update(overrides)
    return build_chat_completions_request(**defaults)


def test_build_chat_completions_request_uses_json_schema_response_format():
    request = _build_request_with_defaults()

    assert request["response_format"]["type"] == "json_schema"


def test_build_chat_completions_request_pins_schema_name_and_strict_true():
    request = _build_request_with_defaults()

    json_schema = request["response_format"]["json_schema"]
    assert json_schema["name"] == "tgm_response"
    assert json_schema["strict"] is True
    assert json_schema["schema"] is _PER_CHAT_SCHEMA


def test_build_chat_completions_request_emits_two_messages_in_order():
    request = _build_request_with_defaults(system="SYS", user="USR")

    assert request["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USR"},
    ]


def test_build_chat_completions_request_omits_options_when_none():
    request = _build_request_with_defaults(options=None)

    assert "options" not in request


def test_build_chat_completions_request_passes_options_through_when_set():
    request = _build_request_with_defaults(options={"num_ctx": 24576})

    assert request["options"] == {"num_ctx": 24576}


def test_parse_chat_completions_response_extracts_content_as_dict():
    payload = {"choices": [{"message": {"content": json.dumps({"summary": "ok"})}}]}

    assert parse_chat_completions_response(payload) == {"summary": "ok"}


def test_parse_chat_completions_response_raises_on_empty_choices():
    with pytest.raises(LLMResponseError):
        parse_chat_completions_response({"choices": []})


def test_parse_chat_completions_response_raises_on_missing_content():
    payload = {"choices": [{"message": {}}]}

    with pytest.raises(LLMResponseError):
        parse_chat_completions_response(payload)


def test_parse_chat_completions_response_raises_on_invalid_json():
    payload = {"choices": [{"message": {"content": "{not json"}}]}

    with pytest.raises(LLMResponseError):
        parse_chat_completions_response(payload)


def test_check_input_budget_returns_estimated_tokens_when_within_limit():
    system = "system prompt"
    user = "user prompt"

    expected = estimate_tokens(system) + estimate_tokens(user)

    assert check_input_budget(system, user, max_input_tokens=10_000) == expected


def test_check_input_budget_raises_when_exceeded():
    long_text = "a" * 30_000

    with pytest.raises(LLMBudgetExceededError):
        check_input_budget(long_text, "tail", max_input_tokens=100)
