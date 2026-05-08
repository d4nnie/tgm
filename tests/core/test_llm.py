import asyncio
from typing import Any

from tgm.core.llm import JsonSchema, LLMBudgetExceededError, LLMProvider

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
