import json
from datetime import UTC, datetime

import click
from sqlalchemy import select
from sqlalchemy.orm import Session

from tgm.cli.auth import run_with_session_guard
from tgm.cli.prompts import make_click_login_callbacks, make_click_status_callback
from tgm.core.errors import StatusCallback
from tgm.core.parsing import classify_telethon_entity, extract_entity_display_name
from tgm.core.types import Chat
from tgm.shell.client import fetch_dialogs, login
from tgm.shell.db import DatabaseHandle
from tgm.shell.orm import ChatRow
from tgm.shell.platform import require_single_instance
from tgm.shell.repos import (
    get_chat_profile,
    is_chat_monitored,
    mark_chat_unmonitored,
    update_chat_period,
    upsert_chat,
    upsert_chat_profile_description,
)
from tgm.shell.retry import do_with_telethon_guard


@click.group(name="chat")
def chat_group() -> None:
    """Chat whitelist: list, add, remove, profile."""


@chat_group.command(name="list")
@click.pass_obj
@require_single_instance
def chat_list(handle: DatabaseHandle) -> None:
    """Print all dialogs in the account as JSON."""
    run_with_session_guard(_run_chat_list(handle))


@chat_group.command(name="add")
@click.argument("chat_id", type=int)
@click.option("--period", type=int, default=30, help="Per-chat tick period in minutes.")
@click.pass_obj
@require_single_instance
def chat_add(handle: DatabaseHandle, chat_id: int, period: int) -> None:
    """Add a chat to the whitelist (no backfill)."""
    run_with_session_guard(_run_chat_add(handle, chat_id, period))


@chat_group.command(name="remove")
@click.argument("chat_id", type=int)
@click.pass_obj
def chat_remove(handle: DatabaseHandle, chat_id: int) -> None:
    """Remove a chat from the whitelist (history retained)."""
    with handle.session_factory() as session:
        mark_chat_unmonitored(session, chat_id)
        session.commit()
    click.echo(json.dumps({"chat_id": chat_id, "is_monitored": False}, ensure_ascii=False))


@chat_group.command(name="profile")
@click.argument("chat_id", type=int)
@click.option("--description", type=str, default=None, help="Chat description prompt.")
@click.option("--period", type=int, default=None, help="Per-chat tick period in minutes.")
@click.pass_obj
def chat_profile(handle: DatabaseHandle, chat_id: int, description: str | None, period: int | None) -> None:
    """Show or edit chat profile."""
    with handle.session_factory() as session:
        if (description is not None or period is not None) and not _chat_exists(session, chat_id):
            raise click.ClickException(f"chat_id={chat_id} not in whitelist; run `chat add {chat_id}` first")
        if description is not None:
            upsert_chat_profile_description(
                session,
                chat_id=chat_id,
                description_prompt=description,
                now=datetime.now(UTC),
            )
        if period is not None:
            update_chat_period(session, chat_id=chat_id, period_n_minutes=period)
        if description is not None or period is not None:
            session.commit()
        payload = _read_chat_profile_payload(session, chat_id)
    click.echo(json.dumps(payload, ensure_ascii=False))


def _chat_exists(session: Session, chat_id: int) -> bool:
    return session.execute(select(ChatRow.chat_id).where(ChatRow.chat_id == chat_id)).scalar_one_or_none() is not None


def _read_chat_profile_payload(session: Session, chat_id: int) -> dict[str, object]:
    chat_period = session.execute(
        select(ChatRow.period_n_minutes).where(ChatRow.chat_id == chat_id)
    ).scalar_one_or_none()
    profile = get_chat_profile(session, chat_id)
    return {
        "chat_id": chat_id,
        "description_prompt": profile.description_prompt if profile else "",
        "rolling_summary": profile.rolling_summary if profile else "",
        "period_n_minutes": int(chat_period) if chat_period is not None else None,
    }


async def _run_chat_list(handle: DatabaseHandle) -> None:
    status_callback = make_click_status_callback()
    client = await login(make_click_login_callbacks(), status_callback)
    try:
        dialogs = await fetch_dialogs(client)
        with handle.session_factory() as session:
            payload = [
                {
                    "chat_id": dialog.chat_id,
                    "title": dialog.title,
                    "type": dialog.chat_type,
                    "is_monitored": is_chat_monitored(session, dialog.chat_id),
                }
                for dialog in dialogs
            ]
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    finally:
        await client.disconnect()


async def _run_chat_add(handle: DatabaseHandle, chat_id: int, period_n_minutes: int) -> None:
    status_callback = make_click_status_callback()
    client = await login(make_click_login_callbacks(), status_callback)
    try:
        entity = await _fetch_entity(client, chat_id, status_callback)
        chat = Chat(
            chat_id=chat_id,
            title=extract_entity_display_name(entity),
            chat_type=classify_telethon_entity(entity),
            is_monitored=True,
            period_n_minutes=period_n_minutes,
            added_at=datetime.now(UTC),
        )
        with handle.session_factory() as session:
            upsert_chat(session, chat)
            session.commit()
        click.echo(
            json.dumps(
                {
                    "chat_id": chat.chat_id,
                    "title": chat.title,
                    "type": chat.chat_type,
                    "is_monitored": True,
                    "period_n_minutes": chat.period_n_minutes,
                },
                ensure_ascii=False,
            )
        )
    finally:
        await client.disconnect()


async def _fetch_entity(client: object, chat_id: int, status_callback: StatusCallback) -> object:
    return await do_with_telethon_guard(
        lambda: client.get_entity(chat_id),  # ty: ignore[unresolved-attribute]
        status_callback,
    )
