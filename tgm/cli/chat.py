import asyncio
import json
from datetime import UTC, datetime

import click

from tgm.cli.prompts import make_click_login_callbacks
from tgm.cli.stubs import stub_not_implemented
from tgm.core.parsing import classify_telethon_entity, extract_entity_display_name
from tgm.core.types import Chat
from tgm.shell.client import login
from tgm.shell.db import connect, resolve_db_path
from tgm.shell.repos import is_chat_monitored, mark_chat_unmonitored, upsert_chat


@click.group(name="chat")
def chat_group() -> None:
    """Chat whitelist: list, add, remove, profile."""


@chat_group.command(name="list")
def chat_list() -> None:
    """Print all dialogs in the account as JSON."""
    asyncio.run(_run_chat_list())


@chat_group.command(name="add")
@click.argument("chat_id", type=int)
@click.option("--period", type=int, default=30, help="Per-chat tick period in minutes.")
def chat_add(chat_id: int, period: int) -> None:
    """Add a chat to the whitelist (no backfill)."""
    asyncio.run(_run_chat_add(chat_id, period))


@chat_group.command(name="remove")
@click.argument("chat_id", type=int)
def chat_remove(chat_id: int) -> None:
    """Remove a chat from the whitelist (history retained)."""
    connection = connect(resolve_db_path())
    try:
        mark_chat_unmonitored(connection, chat_id)
    finally:
        connection.close()
    click.echo(json.dumps({"chat_id": chat_id, "is_monitored": False}, ensure_ascii=False))


@chat_group.command(name="profile")
@click.argument("chat_id", type=int)
@click.option("--description", type=str, default=None, help="Chat description prompt.")
@click.option("--period", type=int, default=None, help="Per-chat tick period in minutes.")
def chat_profile(chat_id: int, description: str | None, period: int | None) -> None:
    """Show or edit chat profile."""
    stub_not_implemented("EPIC-04 (repos)")


async def _run_chat_list() -> None:
    client = await login(make_click_login_callbacks())
    connection = connect(resolve_db_path())
    try:
        dialogs_payload = []
        async for dialog in client.iter_dialogs():
            dialog_id = int(dialog.id)
            dialogs_payload.append(
                {
                    "chat_id": dialog_id,
                    "title": extract_entity_display_name(dialog.entity),
                    "type": classify_telethon_entity(dialog.entity),
                    "is_monitored": is_chat_monitored(connection, dialog_id),
                }
            )
        click.echo(json.dumps(dialogs_payload, ensure_ascii=False, indent=2))
    finally:
        connection.close()
        await client.disconnect()


async def _run_chat_add(chat_id: int, period_n_minutes: int) -> None:
    client = await login(make_click_login_callbacks())
    connection = connect(resolve_db_path())
    try:
        entity = await client.get_entity(chat_id)
        chat = Chat(
            chat_id=chat_id,
            title=extract_entity_display_name(entity),
            chat_type=classify_telethon_entity(entity),
            is_monitored=True,
            period_n_minutes=period_n_minutes,
            added_at=datetime.now(UTC),
        )
        upsert_chat(connection, chat)
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
        connection.close()
        await client.disconnect()
