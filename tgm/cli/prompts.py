import asyncio
import functools

import click

from tgm.core.errors import StatusCallback
from tgm.shell.client import LoginCallbacks


def make_click_status_callback() -> StatusCallback:
    return lambda message: click.echo(message, err=True)


def make_click_login_callbacks() -> LoginCallbacks:
    return LoginCallbacks(
        request_api_id=functools.partial(_prompt_int, "api_id (from my.telegram.org)"),
        request_api_hash=functools.partial(_prompt_secret, "api_hash"),
        request_phone=functools.partial(_prompt_text, "phone (e.g. +79991234567)"),
        request_sms_code=functools.partial(_prompt_text, "SMS code"),
        request_password=functools.partial(_prompt_secret, "2FA password"),
    )


async def _prompt_int(label: str) -> int:
    return await asyncio.to_thread(click.prompt, label, type=int)


async def _prompt_text(label: str) -> str:
    return await asyncio.to_thread(click.prompt, label, type=str)


async def _prompt_secret(label: str) -> str:
    return await asyncio.to_thread(click.prompt, label, type=str, hide_input=True)
