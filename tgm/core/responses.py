from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from tgm.core.llm import LLMResponseError
from tgm.core.schemas import (
    CriteriaRecalcResponse,
    GlobalResponse,
    PerChatResponse,
)

_PydanticModel = TypeVar("_PydanticModel", bound=BaseModel)


def parse_per_chat_response(payload: Mapping[str, Any], *, known_message_ids: set[int]) -> PerChatResponse:
    response = _model_validate_or_wrap(PerChatResponse, payload)
    _require_non_empty(response.summary, "summary")
    _require_non_empty(response.updated_rolling_summary, "updated_rolling_summary")
    for highlight in response.highlights:
        _require_non_empty(highlight.why, "highlights[].why")
        if highlight.message_id not in known_message_ids:
            raise LLMResponseError(f"highlight references unknown message_id={highlight.message_id}")
    return response


def parse_global_response(
    payload: Mapping[str, Any],
    *,
    known_chat_message_pairs: set[tuple[int, int]],  # noqa: WPS221  # parameterised-type signature
) -> GlobalResponse:
    response = _model_validate_or_wrap(GlobalResponse, payload)
    _require_non_empty(response.summary, "summary")
    for highlight in response.highlights:
        _require_non_empty(highlight.why, "highlights[].why")
        pair = (highlight.chat_id, highlight.message_id)
        if pair not in known_chat_message_pairs:
            raise LLMResponseError(
                f"highlight references unknown (chat_id={highlight.chat_id}, message_id={highlight.message_id})"
            )
    return response


def parse_criteria_response(payload: Mapping[str, Any]) -> CriteriaRecalcResponse:
    response = _model_validate_or_wrap(CriteriaRecalcResponse, payload)
    _require_non_empty(response.new_criteria_text, "new_criteria_text")
    _require_non_empty(response.what_changed, "what_changed")
    return response


def _model_validate_or_wrap(model_class: type[_PydanticModel], payload: Mapping[str, Any]) -> _PydanticModel:
    try:
        return model_class.model_validate(dict(payload))
    except ValidationError as error:
        raise LLMResponseError(f"response does not match {model_class.__name__} schema: {error}") from error


def _require_non_empty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise LLMResponseError(f"field {field_name!r} must be a non-empty string")
