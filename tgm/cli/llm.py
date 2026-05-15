import asyncio
import json
import time

import click
import httpx
from pydantic import ValidationError

from tgm.core.llm import LLMResponseError, LLMUnavailableError
from tgm.core.schemas import PING_RESPONSE_SCHEMA, PingResponse
from tgm.core.types import LlmProviderConfig
from tgm.shell.config import load_llm_provider_config, save_llm_provider_config
from tgm.shell.llm import build_provider
from tgm.shell.llm.openaicompat import OpenAiCompatibleProvider

_PING_SYSTEM_PROMPT = "Reply with valid JSON. Set the `answer` field to the literal string `pong`."
_PING_USER_PROMPT = "ping"
_PING_MAX_INPUT_TOKENS = 4000


@click.group(name="llm")
def llm_group() -> None:
    """LLM provider commands."""


@llm_group.command(name="test")
def llm_test() -> None:
    """Ping the configured provider; print model and latency as JSON."""
    try:
        config = load_llm_provider_config()
    except ValueError as error:
        click.echo(
            json.dumps({"status": "error", "category": "config", "error": str(error)}, ensure_ascii=False),
            err=True,
        )
        raise click.exceptions.Exit(4) from error

    exit_code = asyncio.run(_smoke_provider(config))
    if exit_code != 0:
        raise click.exceptions.Exit(exit_code)


async def _smoke_provider(config: LlmProviderConfig) -> int:
    provider = build_provider(config)
    started_at = time.monotonic()
    try:
        return await _call_and_report(provider, config, started_at)
    finally:
        await provider.aclose()


async def _call_and_report(provider: OpenAiCompatibleProvider, config: LlmProviderConfig, started_at: float) -> int:
    try:
        raw = await provider.call_json(
            system=_PING_SYSTEM_PROMPT,
            user=_PING_USER_PROMPT,
            schema=PING_RESPONSE_SCHEMA,
            max_input_tokens=_PING_MAX_INPUT_TOKENS,
        )
        parsed = PingResponse.model_validate(raw)
    except httpx.ConnectError as error:
        click.echo(
            json.dumps(
                {"status": "error", "category": "unreachable", "base_url": config.base_url, "error": str(error)},
                ensure_ascii=False,
            ),
            err=True,
        )
        return 1
    except LLMUnavailableError as error:
        click.echo(
            json.dumps({"status": "error", "category": "unavailable", "error": str(error)}, ensure_ascii=False),
            err=True,
        )
        return 1
    except httpx.HTTPStatusError as error:
        return _report_http_error(error, config)
    except (LLMResponseError, ValidationError) as error:
        click.echo(
            json.dumps({"status": "error", "category": "malformed_json", "error": str(error)}, ensure_ascii=False),
            err=True,
        )
        return 3

    latency_ms = int((time.monotonic() - started_at) * 1000)
    click.echo(
        json.dumps(
            {
                "status": "ok",
                "model": config.model,
                "latency_ms": latency_ms,
                "answer": parsed.answer,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _report_http_error(error: httpx.HTTPStatusError, config: LlmProviderConfig) -> int:
    status_code = error.response.status_code
    if status_code == 404:
        click.echo(
            json.dumps(
                {"status": "error", "category": "model_not_found", "model": config.model, "base_url": config.base_url},
                ensure_ascii=False,
            ),
            err=True,
        )
        return 2
    click.echo(
        json.dumps(
            {"status": "error", "category": "http", "http_status": status_code, "base_url": config.base_url},
            ensure_ascii=False,
        ),
        err=True,
    )
    return 2


@llm_group.group(name="config")
def llm_config_group() -> None:
    """Show or update LLM provider configuration. --options stay manual in TOML."""


@llm_config_group.command(name="show")
def llm_config_show() -> None:
    """Print current [llm] section as JSON."""
    try:
        config = load_llm_provider_config()
    except ValueError as error:
        click.echo(
            json.dumps({"status": "error", "category": "config", "error": str(error)}, ensure_ascii=False),
            err=True,
        )
        raise click.exceptions.Exit(4) from error
    click.echo(
        json.dumps(
            {
                "provider": config.provider,
                "base_url": config.base_url,
                "model": config.model,
                "api_key_env": config.api_key_env,
                "allow_hosts": config.allow_hosts,
                "options": config.options,
            },
            ensure_ascii=False,
        )
    )


@llm_config_group.command(name="set")
@click.option("--base-url", type=str, default=None, help="LLM base URL (must satisfy llm.allow_hosts).")
@click.option("--model", type=str, default=None, help="Model identifier.")
@click.option("--api-key-env", type=str, default=None, help="Name of the env var holding the API key.")
@click.option(
    "--allow-host",
    "allow_hosts",
    type=str,
    multiple=True,
    help="Hostname(s) permitted for non-loopback base_url. Pass multiple times to set the full list.",
)
def llm_config_set(
    base_url: str | None,
    model: str | None,
    api_key_env: str | None,
    allow_hosts: tuple[str, ...],
) -> None:
    """Update individual fields atomically. Only the fields you pass are changed."""
    current = load_llm_provider_config()
    new_config = LlmProviderConfig(
        provider=current.provider,
        base_url=base_url if base_url is not None else current.base_url,
        model=model if model is not None else current.model,
        api_key_env=api_key_env if api_key_env is not None else current.api_key_env,
        options=current.options,
        allow_hosts=list(allow_hosts) if allow_hosts else current.allow_hosts,
    )
    try:
        save_llm_provider_config(new_config)
        reloaded = load_llm_provider_config()
    except ValueError as error:
        click.echo(
            json.dumps({"status": "error", "category": "config", "error": str(error)}, ensure_ascii=False),
            err=True,
        )
        raise click.exceptions.Exit(4) from error
    click.echo(
        json.dumps(
            {
                "status": "ok",
                "provider": reloaded.provider,
                "base_url": reloaded.base_url,
                "model": reloaded.model,
                "api_key_env": reloaded.api_key_env,
                "allow_hosts": reloaded.allow_hosts,
            },
            ensure_ascii=False,
        )
    )
