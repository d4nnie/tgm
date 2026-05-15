import asyncio
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, NoReturn

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


@dataclass(frozen=True)
class _HttpAttemptResult:
    parsed: dict[str, Any] | None
    status: int | None
    retry_after: int | None
    error: Exception | None


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
        async with self._lock:
            return await self._post_with_retries(
                url=f"{self._base_url}{_CHAT_COMPLETIONS_PATH}",
                headers=self._build_headers(),
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
            parsed, attempt, last_log_signature = await self._run_one_attempt(
                url,
                headers,
                request_body,
                prompt_chars,
                prompt_tokens_estimated,
                attempt,
                last_log_signature,
            )
            if parsed is not None:
                return parsed

    async def _run_one_attempt(
        self,
        url: str,
        headers: dict[str, str],
        request_body: dict[str, Any],
        prompt_chars: int,
        prompt_tokens_estimated: int,
        attempt: int,
        last_log_signature: tuple[str, int] | None,
    ) -> tuple[dict[str, Any] | None, int, tuple[str, int] | None]:  # noqa: WPS221  # parameterised-type return signature
        started_at = time.monotonic()
        result = await self._attempt_post(url, headers, request_body)
        if result.parsed is not None:
            self._log_success(
                attempt,
                prompt_chars,
                prompt_tokens_estimated,
                started_at,
            )
            return result.parsed, attempt, last_log_signature
        outcome = classify_http_outcome(
            status=result.status,
            attempt=attempt,
            retry_after=result.retry_after,
        )
        if outcome is None:
            self._raise_unavailable(
                prompt_chars,
                prompt_tokens_estimated,
                started_at,
                result,
            )
        signature = await self._sleep_before_retry(
            outcome,
            result.status,
            last_log_signature,
        )
        return None, outcome.attempt + 1, signature

    def _raise_unavailable(
        self,
        prompt_chars: int,
        prompt_tokens_estimated: int,
        started_at: float,
        result: _HttpAttemptResult,
    ) -> NoReturn:
        self._log_failure(prompt_chars, prompt_tokens_estimated, started_at, result.status)
        raise LLMUnavailableError(_describe_failure(result.status, result.error)) from result.error

    async def _sleep_before_retry(
        self,
        outcome: object,
        status: int | None,
        last_log_signature: tuple[str, int] | None,  # noqa: WPS221  # parameterised-type signature
    ) -> tuple[str, int]:
        signature = _log_retry_state(
            attempt=outcome.attempt,  # ty: ignore[unresolved-attribute]
            wait_seconds=outcome.wait_seconds,  # ty: ignore[unresolved-attribute]
            status=status,
            last_signature=last_log_signature,
            model=self._model,
        )
        await asyncio.sleep(outcome.wait_seconds)  # ty: ignore[unresolved-attribute]
        return signature

    async def _attempt_post(
        self,
        url: str,
        headers: dict[str, str],
        request_body: dict[str, Any],  # noqa: WPS221  # parameterised-type signature
    ) -> _HttpAttemptResult:
        try:
            response = await self._client.post(url, json=request_body, headers=headers)
            response.raise_for_status()
            parsed = parse_chat_completions_response(response.json())
        except httpx.TimeoutException as error:
            return _HttpAttemptResult(
                parsed=None,
                status=None,
                retry_after=None,
                error=error,
            )
        except httpx.HTTPStatusError as error:
            retry_after = _parse_retry_after(error.response.headers.get("Retry-After"))
            return _HttpAttemptResult(
                parsed=None,
                status=error.response.status_code,
                retry_after=retry_after,
                error=error,
            )
        except httpx.HTTPError as error:
            return _HttpAttemptResult(
                parsed=None,
                status=None,
                retry_after=None,
                error=error,
            )
        return _HttpAttemptResult(
            parsed=parsed,
            status=None,
            retry_after=None,
            error=None,
        )

    def _log_success(self, attempt: int, prompt_chars: int, prompt_tokens_estimated: int, started_at: float) -> None:
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

    def _log_failure(
        self, prompt_chars: int, prompt_tokens_estimated: int, started_at: float, status: int | None
    ) -> None:
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
