import asyncio
import functools

import click
from telethon.tl.types import User

from tgm.cli.stubs import stub_not_implemented
from tgm.shell.client import LoginCallbacks, login


@click.group(name="auth")
def auth_group() -> None:
    """Telegram session: login and status."""


@auth_group.command(name="login")
def auth_login() -> None:
    """Interactive login: api_id / api_hash / phone / SMS code / 2FA."""
    asyncio.run(_run_login())


@auth_group.command(name="status")
def auth_status() -> None:
    """Print JSON: connection, provider, worker state."""
    stub_not_implemented("EPIC-05 (LLM provider) + EPIC-07 (worker)")


async def _run_login() -> None:
    callbacks = LoginCallbacks(
        request_api_id=functools.partial(_prompt_int, "api_id (from my.telegram.org)"),
        request_api_hash=functools.partial(_prompt_secret, "api_hash"),
        request_phone=functools.partial(_prompt_text, "phone (e.g. +79991234567)"),
        request_sms_code=functools.partial(_prompt_text, "SMS code"),
        request_password=functools.partial(_prompt_secret, "2FA password"),
    )

    client = await login(callbacks)
    try:
        me = await client.get_me()
        if isinstance(me, User):
            click.echo(f"Logged in as {me.first_name} (id={me.id})")
        else:
            click.echo("Logged in")
    finally:
        await client.disconnect()


async def _prompt_int(label: str) -> int:
    return await asyncio.to_thread(click.prompt, label, type=int)


async def _prompt_text(label: str) -> str:
    return await asyncio.to_thread(click.prompt, label, type=str)


async def _prompt_secret(label: str) -> str:
    return await asyncio.to_thread(click.prompt, label, type=str, hide_input=True)
