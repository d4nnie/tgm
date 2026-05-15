import asyncio
import json
import time

import click
import httpx
from pydantic import ValidationError

from tgm.core.llm import LLMResponseError, LLMUnavailableError
from tgm.core.schemas import PING_RESPONSE_SCHEMA, PingResponse
from tgm.core.types import LlmProviderConfig
from tgm.shell.config import load_llm_provider_config
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
