import asyncio
import time
from typing import cast

import click
import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from tgm.core.llm import LLMResponseError
from tgm.core.types import LlmProviderConfig
from tgm.shell.config import load_llm_provider_config
from tgm.shell.llm import build_provider
from tgm.shell.llm.openaicompat import OpenAiCompatibleProvider


class _PingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str


_PING_SCHEMA = _PingResponse.model_json_schema()
_PING_SYSTEM_PROMPT = "Reply with valid JSON. Set the `answer` field to the literal string `pong`."
_PING_USER_PROMPT = "ping"
_PING_MAX_INPUT_TOKENS = 4000


@click.group(name="llm")
def llm_group() -> None:
    """LLM provider commands."""


@llm_group.command(name="test")
def llm_test() -> None:
    """Ping the configured provider; print model and latency."""
    try:
        config = load_llm_provider_config()
    except ValueError as error:
        click.echo(f"error: invalid [llm] config: {error}", err=True)
        raise click.exceptions.Exit(4) from error

    exit_code = asyncio.run(_smoke_provider(config))
    if exit_code != 0:
        raise click.exceptions.Exit(exit_code)


async def _smoke_provider(config: LlmProviderConfig) -> int:
    # MVP factory only ever returns OpenAi-compatible. Cast so we can call aclose,
    # which isn't part of the LLMProvider Protocol on purpose.
    provider = cast(OpenAiCompatibleProvider, build_provider(config))
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
            schema=_PING_SCHEMA,
            max_input_tokens=_PING_MAX_INPUT_TOKENS,
        )
        parsed = _PingResponse.model_validate(raw)
    except httpx.ConnectError:
        click.echo(f"error: LLM unreachable at {config.base_url}", err=True)
        return 1
    except httpx.HTTPStatusError as error:
        return _report_http_error(error, config)
    except (LLMResponseError, ValidationError) as error:
        click.echo(f"error: provider returned malformed JSON: {error}", err=True)
        return 3

    latency_ms = int((time.monotonic() - started_at) * 1000)
    click.echo(f"ok: model={config.model} latency_ms={latency_ms} answer={parsed.answer!r}")
    return 0


def _report_http_error(error: httpx.HTTPStatusError, config: LlmProviderConfig) -> int:
    if error.response.status_code == 404:
        click.echo(f"error: model {config.model!r} not available at {config.base_url}", err=True)
        return 2
    click.echo(f"error: HTTP {error.response.status_code} from {config.base_url}", err=True)
    return 2
