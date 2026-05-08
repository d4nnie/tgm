from typing import Final

from pydantic import BaseModel, ConfigDict

from tgm.core.llm import JsonSchema

_STRICT_PAYLOAD = ConfigDict(extra="forbid")


class PerChatHighlight(BaseModel):
    model_config = _STRICT_PAYLOAD

    message_id: int
    why: str


class PerChatResponse(BaseModel):
    model_config = _STRICT_PAYLOAD

    summary: str
    highlights: list[PerChatHighlight]
    updated_rolling_summary: str


class GlobalHighlight(BaseModel):
    model_config = _STRICT_PAYLOAD

    chat_id: int
    message_id: int
    why: str


class GlobalResponse(BaseModel):
    model_config = _STRICT_PAYLOAD

    summary: str
    highlights: list[GlobalHighlight]


class CriteriaRecalcResponse(BaseModel):
    model_config = _STRICT_PAYLOAD

    new_criteria_text: str
    what_changed: str


PER_CHAT_RESPONSE_SCHEMA: Final[JsonSchema] = PerChatResponse.model_json_schema()
GLOBAL_RESPONSE_SCHEMA: Final[JsonSchema] = GlobalResponse.model_json_schema()
CRITERIA_RECALC_RESPONSE_SCHEMA: Final[JsonSchema] = CriteriaRecalcResponse.model_json_schema()
