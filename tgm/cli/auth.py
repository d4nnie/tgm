import asyncio
import json
import os
import sys
from collections.abc import Coroutine
from typing import Any

import click
from telethon.tl.types import User

from tgm.cli.prompts import (
    make_click_login_callbacks,
    make_click_status_callback,
    make_env_login_callbacks,
)
from tgm.cli.stubs import stub_not_implemented
from tgm.core.errors import SessionExpiredError
from tgm.shell.client import LoginCallbacks, login, resolve_session_path
from tgm.shell.platform import require_single_instance
from tgm.shell.retry import do_with_telethon_guard


@click.group(name="auth")
def auth_group() -> None:
    """Telegram session: login and status."""


@auth_group.command(name="login")
@click.option(
    "--non-interactive",
    is_flag=True,
    default=False,
    help="Read credentials from TGM_* env vars instead of prompting.",
)
@require_single_instance
def auth_login(non_interactive: bool) -> None:
    """Interactive login: api_id / api_hash / phone / SMS code / 2FA."""
    callbacks = make_env_login_callbacks(os.environ) if non_interactive else make_click_login_callbacks()
    run_with_session_guard(_run_login(callbacks))


@auth_group.command(name="status")
@require_single_instance
def auth_status() -> None:
    """Print JSON: connection, provider, worker state."""
    stub_not_implemented("EPIC-05 (LLM provider) + EPIC-07 (worker)")


@auth_group.command(name="check")
def auth_check() -> None:
    """Detect whether a Telegram session file exists locally (no RPC)."""
    session_path = resolve_session_path()
    if session_path.exists():
        click.echo(json.dumps({"status": "ok", "session": str(session_path)}, ensure_ascii=False))
        return
    click.echo(
        json.dumps({"status": "error", "error": "no session configured"}, ensure_ascii=False),
        err=True,
    )
    raise click.exceptions.Exit(2)


def run_with_session_guard(coroutine: Coroutine[Any, Any, None]) -> None:
    try:
        asyncio.run(coroutine)
    except SessionExpiredError as error:
        click.echo(f"Error: {error}", err=True)
        sys.exit(2)


async def _run_login(callbacks: LoginCallbacks) -> None:
    status_callback = make_click_status_callback()
    client = await login(callbacks, status_callback)
    try:
        me = await do_with_telethon_guard(lambda: client.get_me(), status_callback)
        if isinstance(me, User):
            click.echo(f"Logged in as {me.first_name} (id={me.id})")
        else:
            click.echo("Logged in")
    finally:
        await client.disconnect()
