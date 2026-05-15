import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime

import click
from sqlalchemy.orm import Session

from tgm.core.errors import SingleInstanceError
from tgm.core.feedback import build_feedback_samples, group_feedback_by_chat
from tgm.core.prompts import build_criteria_recalc_prompt
from tgm.core.responses import parse_criteria_response
from tgm.core.schemas import CRITERIA_RECALC_RESPONSE_SCHEMA, CriteriaRecalcResponse
from tgm.core.scopes import parse_chat_scope
from tgm.core.types import Feedback, FeedbackSample
from tgm.shell.config import load_llm_provider_config
from tgm.shell.db import DatabaseHandle
from tgm.shell.llm import LlmProvider, build_provider
from tgm.shell.platform import acquire_exclusive_lock
from tgm.shell.repos import (
    get_active_criteria,
    get_criteria_by_version,
    get_messages_by_ids,
    get_unconsumed_feedback,
    get_user_profile_about_me,
    insert_criteria,
    mark_feedback_consumed,
)

_RECALC_MAX_INPUT_TOKENS = 16000


@dataclass(frozen=True)
class _InputsToRecalcBatch:
    old_version: int
    current_text: str
    samples: list[FeedbackSample]
    about_me: str
    consumed_feedback_ids: list[int]


@click.group(name="criteria")
def criteria_group() -> None:
    """Importance criteria: show, recalc, rollback."""


@criteria_group.command(name="show")
@click.option("--scope", type=str, default="global", help="global | chat:<id>.")
@click.pass_obj
def criteria_show(handle: DatabaseHandle, scope: str) -> None:
    """Print active criteria text as JSON. For chat:<id> falls back to global if no override."""
    with handle.session_factory() as session:
        criteria = get_active_criteria(session, scope)
        inherited = False
        if criteria is None and scope.startswith("chat:"):
            criteria = get_active_criteria(session, "global")
            inherited = criteria is not None
    if criteria is None:
        click.echo(json.dumps({"scope": scope, "criteria_text": None, "version": None}, ensure_ascii=False))
        return
    click.echo(
        json.dumps(
            {
                "scope": scope,
                "effective_scope": criteria.scope,
                "inherited": inherited,
                "version": criteria.version,
                "criteria_text": criteria.criteria_text,
                "updated_at": criteria.updated_at.isoformat(),
            },
            ensure_ascii=False,
        )
    )


@criteria_group.command(name="recalc")
@click.option("--scope", type=str, required=True, help="global | chat:<id>.")
@click.pass_obj
def criteria_recalc(handle: DatabaseHandle, scope: str) -> None:
    """Recalculate criteria from accumulated feedback."""
    try:
        with acquire_exclusive_lock("recalc"):
            asyncio.run(_run_recalc(handle, scope))
    except SingleInstanceError as error:
        raise click.ClickException(f"criteria recalc already running: {error}") from error


@criteria_group.command(name="rollback")
@click.option("--scope", type=str, required=True, help="global | chat:<id>.")
@click.option("--version", type=int, required=True, help="Target version to roll back to.")
@click.pass_obj
def criteria_rollback(handle: DatabaseHandle, scope: str, version: int) -> None:
    """Roll back criteria to a specific version (insert it as the new latest)."""
    with handle.session_factory() as session:
        target = get_criteria_by_version(session, scope=scope, version=version)
        if target is None:
            raise click.ClickException(f"no version {version} for scope {scope!r}")
        active = get_active_criteria(session, scope)
        old_version = active.version if active else None
        new_version = insert_criteria(session, scope=scope, criteria_text=target.criteria_text, now=datetime.now(UTC))
        session.commit()
    click.echo(
        json.dumps(
            {
                "scope": scope,
                "old_version": old_version,
                "new_version": new_version,
                "rolled_back_to": version,
            },
            ensure_ascii=False,
        )
    )


async def _run_recalc(handle: DatabaseHandle, scope: str) -> None:
    config = load_llm_provider_config()
    provider = build_provider(config)
    try:
        inputs = _gather_recalc_inputs(handle, scope)
        parsed = await _call_recalc_llm(provider, inputs)
        new_version = _persist_recalc_result(handle, scope, inputs, parsed.new_criteria_text)
        _emit_recalc_result(scope, inputs, new_version, parsed.what_changed)
    finally:
        await provider.aclose()


async def _call_recalc_llm(provider: LlmProvider, inputs: _InputsToRecalcBatch) -> CriteriaRecalcResponse:
    system, user = build_criteria_recalc_prompt(
        about_me=inputs.about_me,
        current_criteria_text=inputs.current_text,
        feedback_samples=inputs.samples,
    )
    raw = await provider.call_json(
        system=system,
        user=user,
        schema=CRITERIA_RECALC_RESPONSE_SCHEMA,
        max_input_tokens=_RECALC_MAX_INPUT_TOKENS,
    )
    return parse_criteria_response(raw)


def _persist_recalc_result(
    handle: DatabaseHandle, scope: str, inputs: _InputsToRecalcBatch, new_criteria_text: str
) -> int:
    with handle.session_factory() as session:
        new_version = insert_criteria(session, scope=scope, criteria_text=new_criteria_text, now=datetime.now(UTC))
        mark_feedback_consumed(session, inputs.consumed_feedback_ids)
        session.commit()
    return new_version


def _emit_recalc_result(scope: str, inputs: _InputsToRecalcBatch, new_version: int, what_changed: str) -> None:
    click.echo(
        json.dumps(
            {
                "scope": scope,
                "old_version": inputs.old_version,
                "new_version": new_version,
                "what_changed": what_changed,
                "consumed_feedback_ids": inputs.consumed_feedback_ids,
            },
            ensure_ascii=False,
        )
    )


def _gather_recalc_inputs(handle: DatabaseHandle, scope: str) -> _InputsToRecalcBatch:
    feedback_filter, chat_id_filter = _parse_recalc_scope(scope)
    with handle.session_factory() as session:
        return _read_recalc_inputs(session, scope, feedback_filter, chat_id_filter)


def _read_recalc_inputs(
    session: Session, scope: str, feedback_filter: str, chat_id_filter: int | None
) -> _InputsToRecalcBatch:
    current = get_active_criteria(session, scope)
    if current is None:
        raise click.ClickException(f"no active criteria for scope {scope!r}")
    unconsumed = get_unconsumed_feedback(session, scope=feedback_filter, chat_id=chat_id_filter)
    if not unconsumed:
        raise click.ClickException(f"no unconsumed feedback for scope {scope!r}")
    samples = _build_samples_with_one_select_per_chat(session, unconsumed)
    about_me = get_user_profile_about_me(session) or ""
    return _InputsToRecalcBatch(
        old_version=current.version,
        current_text=current.criteria_text,
        samples=samples,
        about_me=about_me,
        consumed_feedback_ids=[feedback.id for feedback in unconsumed],
    )


def _build_samples_with_one_select_per_chat(session: Session, feedback_items: list[Feedback]) -> list[FeedbackSample]:
    grouped = group_feedback_by_chat(feedback_items)
    messages_by_pair = {}
    for chat_id, feedback_for_chat in grouped.items():
        message_ids = sorted({mid for feedback in feedback_for_chat for mid in feedback.message_ids})
        for message in get_messages_by_ids(session, chat_id=chat_id, message_ids=message_ids):
            messages_by_pair[(chat_id, message.message_id)] = message
    return build_feedback_samples(feedback_items, messages_by_pair)


def _parse_recalc_scope(scope: str) -> tuple[str, int | None]:
    try:
        return parse_chat_scope(scope)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error
