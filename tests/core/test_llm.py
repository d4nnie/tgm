import asyncio
import json
from typing import Any

import pytest

from tgm.core.llm import (
    JsonSchema,
    LLMBudgetExceededError,
    LLMProvider,
    LLMResponseError,
    build_chat_completions_request,
    check_input_budget,
    parse_chat_completions_response,
)
from tgm.core.tokens import estimate_tokens

_PER_CHAT_SCHEMA: JsonSchema = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary"],
    "properties": {"summary": {"type": "string"}},
}


class _FakeProvider:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.received_system: str | None = None
        self.received_user: str | None = None
        self.received_schema: JsonSchema | None = None
        self.received_max_input_tokens: int | None = None

    async def call_json(
        self,
        system: str,
        user: str,
        schema: JsonSchema,
        max_input_tokens: int,
    ) -> dict:
        self.received_system = system
        self.received_user = user
        self.received_schema = schema
        self.received_max_input_tokens = max_input_tokens
        return self._response


def _call(provider: _FakeProvider, **kwargs: Any) -> dict:
    return asyncio.run(provider.call_json(**kwargs))


def test_fake_provider_satisfies_protocol_runtime_check():
    fake = _FakeProvider({"summary": "ok"})

    assert isinstance(fake, LLMProvider)


def test_call_json_returns_dict_matching_schema_keys():
    fake = _FakeProvider({"summary": "all quiet"})

    result = _call(
        fake,
        system="sys",
        user="msg",
        schema=_PER_CHAT_SCHEMA,
        max_input_tokens=1024,
    )

    assert isinstance(result, dict)
    for key in _PER_CHAT_SCHEMA["required"]:
        assert key in result


def test_call_json_forwards_arguments():
    fake = _FakeProvider({"summary": "x"})

    _call(
        fake,
        system="be helpful",
        user="hello",
        schema=_PER_CHAT_SCHEMA,
        max_input_tokens=2048,
    )

    assert fake.received_system == "be helpful"
    assert fake.received_user == "hello"
    assert fake.received_schema is _PER_CHAT_SCHEMA
    assert fake.received_max_input_tokens == 2048


def test_llm_budget_exceeded_error_is_runtime_error():
    assert issubclass(LLMBudgetExceededError, RuntimeError)


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
