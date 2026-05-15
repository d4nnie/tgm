from typing import Final

from pydantic import BaseModel, ConfigDict

from tgm.core.llm import JsonSchema

# extra="forbid" gives additionalProperties:false in the schema sent to the
# provider (ADR-0022 strict-mode contract); redundant on parse but the
# fail-fast signal catches provider regressions early.
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


class PingResponse(BaseModel):
    model_config = _STRICT_PAYLOAD

    answer: str


PER_CHAT_RESPONSE_SCHEMA: Final[JsonSchema] = PerChatResponse.model_json_schema()
GLOBAL_RESPONSE_SCHEMA: Final[JsonSchema] = GlobalResponse.model_json_schema()
CRITERIA_RECALC_RESPONSE_SCHEMA: Final[JsonSchema] = CriteriaRecalcResponse.model_json_schema()
PING_RESPONSE_SCHEMA: Final[JsonSchema] = PingResponse.model_json_schema()
