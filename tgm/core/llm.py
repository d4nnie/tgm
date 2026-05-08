import json
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from tgm.core.tokens import estimate_tokens

JsonSchema = dict[str, Any]

_RESPONSE_SCHEMA_NAME = "tgm_response"


class LLMBudgetExceededError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


@runtime_checkable
class LLMProvider(Protocol):
    async def call_json(
        self,
        system: str,
        user: str,
        schema: JsonSchema,
        max_input_tokens: int,
    ) -> dict: ...


def build_chat_completions_request(
    *,
    system: str,
    user: str,
    schema: JsonSchema,
    model: str,
    options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": _RESPONSE_SCHEMA_NAME,
                "schema": schema,
                "strict": True,
            },
        },
    }
    if options:
        request["options"] = dict(options)
    return request


def parse_chat_completions_response(payload: Mapping[str, Any]) -> dict:
    choices = payload.get("choices") or []
    if not choices:
        raise LLMResponseError("Response has no choices")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if content is None:
        raise LLMResponseError("Response message has no content")

    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise LLMResponseError(f"Response content is not valid JSON: {error}") from error


def check_input_budget(system: str, user: str, max_input_tokens: int) -> int:
    estimated = estimate_tokens(system) + estimate_tokens(user)
    if estimated > max_input_tokens:
        raise LLMBudgetExceededError(f"Prompt of {estimated} tokens exceeds {max_input_tokens}-token budget")
    return estimated
