import asyncio
import functools
import json
from collections.abc import Mapping

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


def make_env_login_callbacks(env: Mapping[str, str]) -> LoginCallbacks:
    return LoginCallbacks(
        request_api_id=functools.partial(_read_env_int, env, "TGM_API_ID"),
        request_api_hash=functools.partial(_read_env_str, env, "TGM_API_HASH"),
        request_phone=functools.partial(_read_env_str, env, "TGM_PHONE"),
        request_sms_code=functools.partial(_read_env_str, env, "TGM_SMS_CODE"),
        request_password=functools.partial(_read_env_str, env, "TGM_2FA_PASSWORD"),
    )


async def _prompt_int(label: str) -> int:
    return await asyncio.to_thread(click.prompt, label, type=int)


async def _prompt_text(label: str) -> str:
    return await asyncio.to_thread(click.prompt, label, type=str)


async def _prompt_secret(label: str) -> str:
    return await asyncio.to_thread(click.prompt, label, type=str, hide_input=True)


async def _read_env_str(env: Mapping[str, str], variable_name: str) -> str:
    return _require_env_value(env, variable_name)


async def _read_env_int(env: Mapping[str, str], variable_name: str) -> int:
    value = _require_env_value(env, variable_name)
    try:
        return int(value)
    except ValueError as error:
        click.echo(
            json.dumps(
                {"status": "error", "error": f"{variable_name} must be an integer"},
                ensure_ascii=False,
            ),
            err=True,
        )
        raise click.exceptions.Exit(2) from error


def _require_env_value(env: Mapping[str, str], variable_name: str) -> str:
    value = env.get(variable_name)
    if not value:
        click.echo(
            json.dumps({"status": "error", "error": f"missing {variable_name}"}, ensure_ascii=False),
            err=True,
        )
        raise click.exceptions.Exit(2)
    return value
