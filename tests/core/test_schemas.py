from typing import Any

import pytest
from pydantic import ValidationError

from tgm.core.schemas import (
    CRITERIA_RECALC_RESPONSE_SCHEMA,
    GLOBAL_RESPONSE_SCHEMA,
    PER_CHAT_RESPONSE_SCHEMA,
    CriteriaRecalcResponse,
    GlobalHighlight,
    GlobalResponse,
    PerChatHighlight,
    PerChatResponse,
)


def _per_chat_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "summary": "Discussed deployment plan",
        "highlights": [{"message_id": 1234, "why": "blocker raised"}],
        "updated_rolling_summary": "Team aligned on rollback path",
    }
    base.update(overrides)
    return base


def _global_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "summary": "Overall situation steady",
        "highlights": [{"chat_id": 999, "message_id": 7, "why": "deadline tomorrow"}],
    }
    base.update(overrides)
    return base


def _criteria_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "new_criteria_text": "Updated rules go here",
        "what_changed": "Added a rule about deadlines",
    }
    base.update(overrides)
    return base


def _required_fields(schema: dict[str, Any]) -> list[str]:
    return list(schema["required"])


def _additional_properties(schema: dict[str, Any]) -> Any:
    return schema.get("additionalProperties")


def _nested_definitions(schema: dict[str, Any]) -> dict[str, Any]:
    return schema.get("$defs") or schema.get("definitions") or {}


def test_per_chat_response_validates_well_formed_payload():
    parsed = PerChatResponse.model_validate(_per_chat_payload())

    assert parsed.summary == "Discussed deployment plan"
    assert parsed.highlights == [PerChatHighlight(message_id=1234, why="blocker raised")]
    assert parsed.updated_rolling_summary == "Team aligned on rollback path"


def test_per_chat_response_rejects_payload_missing_required_field():
    payload = _per_chat_payload()
    del payload["updated_rolling_summary"]

    with pytest.raises(ValidationError):
        PerChatResponse.model_validate(payload)


def test_per_chat_response_rejects_payload_with_extra_field():
    with pytest.raises(ValidationError):
        PerChatResponse.model_validate(_per_chat_payload(stray_field="bad"))


def test_per_chat_response_rejects_payload_with_wrong_type():
    bad_payload = _per_chat_payload(highlights=[{"message_id": "not-int", "why": "x"}])

    with pytest.raises(ValidationError):
        PerChatResponse.model_validate(bad_payload)


def test_global_response_validates_well_formed_payload():
    parsed = GlobalResponse.model_validate(_global_payload())

    assert parsed.summary == "Overall situation steady"
    assert parsed.highlights == [GlobalHighlight(chat_id=999, message_id=7, why="deadline tomorrow")]


def test_global_response_rejects_payload_missing_required_field():
    payload = _global_payload()
    del payload["summary"]

    with pytest.raises(ValidationError):
        GlobalResponse.model_validate(payload)


def test_global_response_rejects_payload_with_extra_field():
    with pytest.raises(ValidationError):
        GlobalResponse.model_validate(_global_payload(stray_field="bad"))


def test_global_response_rejects_payload_with_wrong_type():
    bad_payload = _global_payload(highlights=[{"chat_id": 1, "message_id": 7, "why": 42}])

    with pytest.raises(ValidationError):
        GlobalResponse.model_validate(bad_payload)


def test_criteria_recalc_response_validates_well_formed_payload():
    parsed = CriteriaRecalcResponse.model_validate(_criteria_payload())

    assert parsed.new_criteria_text == "Updated rules go here"
    assert parsed.what_changed == "Added a rule about deadlines"


def test_criteria_recalc_response_rejects_payload_missing_required_field():
    payload = _criteria_payload()
    del payload["new_criteria_text"]

    with pytest.raises(ValidationError):
        CriteriaRecalcResponse.model_validate(payload)


def test_criteria_recalc_response_rejects_payload_with_extra_field():
    with pytest.raises(ValidationError):
        CriteriaRecalcResponse.model_validate(_criteria_payload(stray_field="bad"))


def test_criteria_recalc_response_rejects_payload_with_wrong_type():
    with pytest.raises(ValidationError):
        CriteriaRecalcResponse.model_validate(_criteria_payload(new_criteria_text=42))


def test_per_chat_schema_has_additional_properties_false_at_every_object_level():
    assert _additional_properties(PER_CHAT_RESPONSE_SCHEMA) is False
    for definition in _nested_definitions(PER_CHAT_RESPONSE_SCHEMA).values():
        assert _additional_properties(definition) is False, definition


def test_global_schema_has_additional_properties_false_at_every_object_level():
    assert _additional_properties(GLOBAL_RESPONSE_SCHEMA) is False
    for definition in _nested_definitions(GLOBAL_RESPONSE_SCHEMA).values():
        assert _additional_properties(definition) is False, definition


def test_criteria_recalc_schema_has_additional_properties_false():
    assert _additional_properties(CRITERIA_RECALC_RESPONSE_SCHEMA) is False


def test_per_chat_schema_required_fields_match_model():
    assert sorted(_required_fields(PER_CHAT_RESPONSE_SCHEMA)) == sorted(
        ["summary", "highlights", "updated_rolling_summary"]
    )


def test_global_schema_required_fields_match_model():
    assert sorted(_required_fields(GLOBAL_RESPONSE_SCHEMA)) == sorted(["summary", "highlights"])


def test_criteria_recalc_schema_required_fields_match_model():
    assert sorted(_required_fields(CRITERIA_RECALC_RESPONSE_SCHEMA)) == sorted(["new_criteria_text", "what_changed"])
