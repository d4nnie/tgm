import asyncio
import logging
import time
from collections.abc import Mapping
from typing import Any

import httpx

from tgm.core.llm import (
    JsonSchema,
    LLMUnavailableError,
    build_chat_completions_request,
    check_input_budget,
    classify_http_outcome,
    parse_chat_completions_response,
)

logger = logging.getLogger(__name__)

_DEFAULT_REQUEST_TIMEOUT_SECONDS = 120.0
_CHAT_COMPLETIONS_PATH = "/chat/completions"


class OpenAiCompatibleProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model: str,
        options: Mapping[str, Any] | None = None,
        request_timeout_seconds: float = _DEFAULT_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._options = dict(options) if options else None
        self._client = httpx.AsyncClient(timeout=request_timeout_seconds, trust_env=False)
        self._lock = asyncio.Lock()

    async def call_json(
        self,
        system: str,
        user: str,
        schema: JsonSchema,
        max_input_tokens: int,
    ) -> dict[str, Any]:
        prompt_tokens_estimated = check_input_budget(system, user, max_input_tokens)
        prompt_chars = len(system) + len(user)
        request_body = build_chat_completions_request(
            system=system,
            user=user,
            schema=schema,
            model=self._model,
            options=self._options,
        )
        url = f"{self._base_url}{_CHAT_COMPLETIONS_PATH}"
        headers = self._build_headers()

        async with self._lock:
            return await self._post_with_retries(
                url=url,
                headers=headers,
                request_body=request_body,
                prompt_chars=prompt_chars,
                prompt_tokens_estimated=prompt_tokens_estimated,
            )

    async def aclose(self) -> None:
        await self._client.aclose()

    def _build_headers(self) -> dict[str, str]:
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
        return {}

    async def _post_with_retries(
        self,
        *,
        url: str,
        headers: dict[str, str],
        request_body: dict[str, Any],
        prompt_chars: int,
        prompt_tokens_estimated: int,
    ) -> dict[str, Any]:
        attempt = 0
        last_log_signature: tuple[str, int] | None = None
        while True:
            started_at = time.monotonic()
            status: int | None = None
            retry_after: int | None = None
            error_for_raise: Exception | None = None
            try:
                response = await self._client.post(url, json=request_body, headers=headers)
                response.raise_for_status()
                parsed = parse_chat_completions_response(response.json())
            except httpx.TimeoutException as error:
                error_for_raise = error
            except httpx.HTTPStatusError as error:
                error_for_raise = error
                status = error.response.status_code
                retry_after = _parse_retry_after(error.response.headers.get("Retry-After"))
            except httpx.HTTPError as error:
                error_for_raise = error
            else:
                if attempt > 0:
                    logger.info("LLM recovered", extra={"attempt": attempt, "model": self._model})
                logger.info(
                    "Called LLM",
                    extra={
                        "model": self._model,
                        "prompt_chars": prompt_chars,
                        "prompt_tokens_est": prompt_tokens_estimated,
                        "latency_ms": _ms_since(started_at),
                        "success": True,
                    },
                )
                return parsed

            outcome = classify_http_outcome(status=status, attempt=attempt, retry_after=retry_after)
            if outcome is None:
                logger.error(
                    "LLM call failed",
                    extra={
                        "model": self._model,
                        "prompt_chars": prompt_chars,
                        "prompt_tokens_est": prompt_tokens_estimated,
                        "latency_ms": _ms_since(started_at),
                        "success": False,
                        "http_status": status if status is not None else 0,
                    },
                )
                raise LLMUnavailableError(_describe_failure(status, error_for_raise)) from error_for_raise

            last_log_signature = _log_retry_state(
                attempt=outcome.attempt,
                wait_seconds=outcome.wait_seconds,
                status=status,
                last_signature=last_log_signature,
                model=self._model,
            )
            await asyncio.sleep(outcome.wait_seconds)
            attempt += 1


def _log_retry_state(
    *,
    attempt: int,
    wait_seconds: int,
    status: int | None,
    last_signature: tuple[str, int] | None,
    model: str,
) -> tuple[str, int]:
    category = "transport" if status is None else f"http_{status}"
    signature = (category, wait_seconds)
    if signature != last_signature:
        logger.warning(
            "Retrying LLM call",
            extra={
                "model": model,
                "attempt": attempt,
                "sleep_seconds": wait_seconds,
                "category": category,
            },
        )
    return signature


def _parse_retry_after(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _describe_failure(status: int | None, error: Exception | None) -> str:
    if status is None:
        return f"LLM HTTP transport error: {error}"
    return f"LLM HTTP {status}: {error}"


def _ms_since(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)
