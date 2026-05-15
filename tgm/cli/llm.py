import asyncio
import json
import time
from dataclasses import dataclass

import click
import httpx
from pydantic import ValidationError

from tgm.core.llm import LLMResponseError, LLMUnavailableError
from tgm.core.schemas import PING_RESPONSE_SCHEMA, PingResponse
from tgm.core.types import LlmProviderConfig
from tgm.shell.config import load_llm_provider_config, save_llm_provider_config
from tgm.shell.llm import LlmApiKeyMissingError, LlmProvider, build_provider

_PING_SYSTEM_PROMPT = "Reply with valid JSON. Set the `answer` field to the literal string `pong`."
_PING_USER_PROMPT = "ping"
_PING_MAX_INPUT_TOKENS = 4000


@dataclass(frozen=True)
class _SmokeResult:
    exit_code: int
    payload: dict[str, object]
    is_error: bool


@click.group(name="llm")
def llm_group() -> None:
    """LLM provider commands."""


@llm_group.command(name="test")
def llm_test() -> None:
    """Ping the configured provider; print model and latency as JSON."""
    result = _run_smoke_test()
    _emit_smoke_result(result)
    if result.exit_code != 0:
        raise click.exceptions.Exit(result.exit_code)


def _run_smoke_test() -> _SmokeResult:
    try:
        config = load_llm_provider_config()
    except ValueError as error:
        return _smoke_error(4, "config", {"error": str(error)})
    return asyncio.run(_smoke_provider(config))


async def _smoke_provider(config: LlmProviderConfig) -> _SmokeResult:
    try:
        provider = build_provider(config)
    except LlmApiKeyMissingError as error:
        return _smoke_error(4, "config", {"error": str(error)})
    started_at = time.monotonic()
    try:
        return await _call_and_report(provider, config, started_at)
    finally:
        await provider.aclose()


async def _call_and_report(provider: LlmProvider, config: LlmProviderConfig, started_at: float) -> _SmokeResult:
    try:
        raw = await provider.call_json(
            system=_PING_SYSTEM_PROMPT,
            user=_PING_USER_PROMPT,
            schema=PING_RESPONSE_SCHEMA,
            max_input_tokens=_PING_MAX_INPUT_TOKENS,
        )
        parsed = PingResponse.model_validate(raw)
    except (httpx.ConnectError, LLMUnavailableError, httpx.HTTPStatusError, LLMResponseError, ValidationError) as error:
        return _classify_smoke_failure(error, config)
    return _smoke_success(config, parsed.answer, started_at)


def _classify_smoke_failure(error: Exception, config: LlmProviderConfig) -> _SmokeResult:
    if isinstance(error, httpx.ConnectError):
        return _smoke_error(1, "unreachable", {"base_url": config.base_url, "error": str(error)})
    if isinstance(error, LLMUnavailableError):
        return _smoke_error(1, "unavailable", {"error": str(error)})
    if isinstance(error, httpx.HTTPStatusError):
        return _classify_http_failure(error, config)
    return _smoke_error(3, "malformed_json", {"error": str(error)})


def _classify_http_failure(error: httpx.HTTPStatusError, config: LlmProviderConfig) -> _SmokeResult:
    status_code = error.response.status_code
    if status_code == 404:
        return _smoke_error(2, "model_not_found", {"model": config.model, "base_url": config.base_url})
    return _smoke_error(2, "http", {"http_status": status_code, "base_url": config.base_url})


def _smoke_success(config: LlmProviderConfig, answer: str, started_at: float) -> _SmokeResult:
    latency_ms = int((time.monotonic() - started_at) * 1000)
    payload: dict[str, object] = {
        "status": "ok",
        "model": config.model,
        "latency_ms": latency_ms,
        "answer": answer,
    }
    return _SmokeResult(exit_code=0, payload=payload, is_error=False)


def _smoke_error(exit_code: int, category: str, extras: dict[str, object]) -> _SmokeResult:
    payload: dict[str, object] = {"status": "error", "category": category, **extras}
    return _SmokeResult(exit_code=exit_code, payload=payload, is_error=True)


def _emit_smoke_result(result: _SmokeResult) -> None:
    click.echo(json.dumps(result.payload, ensure_ascii=False), err=result.is_error)


@llm_group.group(name="config")
def llm_config_group() -> None:
    """Show or update LLM provider configuration. --options stay manual in TOML."""


@llm_config_group.command(name="show")
def llm_config_show() -> None:
    """Print current [llm] section as JSON."""
    try:
        config = load_llm_provider_config()
    except ValueError as error:
        _emit_config_error(error)
        raise click.exceptions.Exit(4) from error
    click.echo(json.dumps(_render_show_payload(config), ensure_ascii=False))


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
    new_config = _build_updated_llm_config(
        load_llm_provider_config(),
        base_url=base_url,
        model=model,
        api_key_env=api_key_env,
        allow_hosts=allow_hosts,
    )
    try:
        save_llm_provider_config(new_config)
        reloaded = load_llm_provider_config()
    except ValueError as error:
        _emit_config_error(error)
        raise click.exceptions.Exit(4) from error
    click.echo(json.dumps(_render_set_payload(reloaded), ensure_ascii=False))


def _build_updated_llm_config(
    current: LlmProviderConfig,
    *,
    base_url: str | None,
    model: str | None,
    api_key_env: str | None,
    allow_hosts: tuple[str, ...],
) -> LlmProviderConfig:
    return LlmProviderConfig(
        provider=current.provider,
        base_url=base_url if base_url is not None else current.base_url,
        model=model if model is not None else current.model,
        api_key_env=api_key_env if api_key_env is not None else current.api_key_env,
        options=current.options,
        allow_hosts=allow_hosts if allow_hosts else current.allow_hosts,
    )


def _render_show_payload(config: LlmProviderConfig) -> dict[str, object]:
    return {
        "provider": config.provider,
        "base_url": config.base_url,
        "model": config.model,
        "api_key_env": config.api_key_env,
        "allow_hosts": list(config.allow_hosts),
        "options": config.options,
    }


def _render_set_payload(config: LlmProviderConfig) -> dict[str, object]:
    return {
        "status": "ok",
        "provider": config.provider,
        "base_url": config.base_url,
        "model": config.model,
        "api_key_env": config.api_key_env,
        "allow_hosts": list(config.allow_hosts),
    }


def _emit_config_error(error: ValueError) -> None:
    click.echo(
        json.dumps({"status": "error", "category": "config", "error": str(error)}, ensure_ascii=False),
        err=True,
    )
