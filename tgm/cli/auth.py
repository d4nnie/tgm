import asyncio
import sys
from collections.abc import Coroutine
from typing import Any

import click
from telethon.tl.types import User

from tgm.cli.prompts import make_click_login_callbacks, make_click_status_callback
from tgm.cli.stubs import stub_not_implemented
from tgm.core.errors import SessionExpiredError
from tgm.shell.client import login
from tgm.shell.platform import require_single_instance
from tgm.shell.retry import do_with_telethon_guard


@click.group(name="auth")
def auth_group() -> None:
    """Telegram session: login and status."""


@auth_group.command(name="login")
@require_single_instance
def auth_login() -> None:
    """Interactive login: api_id / api_hash / phone / SMS code / 2FA."""
    run_with_session_guard(_run_login())


@auth_group.command(name="status")
@require_single_instance
def auth_status() -> None:
    """Print JSON: connection, provider, worker state."""
    stub_not_implemented("EPIC-05 (LLM provider) + EPIC-07 (worker)")


def run_with_session_guard(coroutine: Coroutine[Any, Any, None]) -> None:
    try:
        asyncio.run(coroutine)
    except SessionExpiredError as error:
        click.echo(f"Error: {error}", err=True)
        sys.exit(2)


async def _run_login() -> None:
    status_callback = make_click_status_callback()
    client = await login(make_click_login_callbacks(), status_callback)
    try:
        me = await do_with_telethon_guard(lambda: client.get_me(), status_callback)
        if isinstance(me, User):
            click.echo(f"Logged in as {me.first_name} (id={me.id})")
        else:
            click.echo("Logged in")
    finally:
        await client.disconnect()
