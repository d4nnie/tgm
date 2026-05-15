import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from tgm.core.tokens import estimate_tokens

JsonSchema = dict[str, Any]

_RESPONSE_SCHEMA_NAME = "tgm_response"
_LLM_MAX_RETRIES = 3
_LLM_BACKOFF_CAP_SECONDS = 60
_LLM_RETRY_AFTER_CAP_SECONDS = 60


class LLMBudgetExceededError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


class LLMUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMHttpRetryOutcome:
    wait_seconds: int
    attempt: int


def classify_http_outcome(
    status: int | None,
    attempt: int,
    retry_after: int | None,
) -> LLMHttpRetryOutcome | None:
    if attempt >= _LLM_MAX_RETRIES:
        return None
    wait_seconds = _wait_seconds_for_status(status, attempt, retry_after)
    if wait_seconds is None:
        return None
    return LLMHttpRetryOutcome(wait_seconds=wait_seconds, attempt=attempt)


def _wait_seconds_for_status(status: int | None, attempt: int, retry_after: int | None) -> int | None:  # noqa: WPS221  # parameterised-type signature
    if status is None:
        return _exponential_backoff(attempt)
    if status == 429:
        return _retry_after_seconds(attempt, retry_after)
    if 500 <= status < 600:
        return _exponential_backoff(attempt)
    return None


def _exponential_backoff(attempt: int) -> int:
    return min(2**attempt, _LLM_BACKOFF_CAP_SECONDS)


def _retry_after_seconds(attempt: int, retry_after: int | None) -> int:
    if retry_after is None or retry_after <= 0:
        return _exponential_backoff(attempt)
    return min(retry_after, _LLM_RETRY_AFTER_CAP_SECONDS)


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


def parse_chat_completions_response(payload: Mapping[str, Any]) -> dict[str, Any]:
    first_choice = _extract_first_choice(payload)
    content = _extract_message_content(first_choice)
    return _decode_json_content(content)


def _extract_first_choice(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    choices = payload.get("choices")
    if not isinstance(choices, list):
        raise LLMResponseError("Response 'choices' is not a list")
    if not choices:
        raise LLMResponseError("Response has no choices")

    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise LLMResponseError("Response 'choices[0]' is not an object")
    return first_choice


def _extract_message_content(first_choice: Mapping[str, Any]) -> str:
    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise LLMResponseError("Response 'choices[0].message' is not an object")

    content = message.get("content")
    if not isinstance(content, str):
        raise LLMResponseError("Response 'choices[0].message.content' is not a string")
    return content


def _decode_json_content(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise LLMResponseError(f"Response content is not valid JSON: {error}") from error


def check_input_budget(system: str, user: str, max_input_tokens: int) -> int:
    estimated = estimate_tokens(system) + estimate_tokens(user)
    if estimated > max_input_tokens:
        raise LLMBudgetExceededError(f"Prompt of {estimated} tokens exceeds {max_input_tokens}-token budget")
    return estimated
