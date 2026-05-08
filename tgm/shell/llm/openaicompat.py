import asyncio
import logging
import time
from collections.abc import Mapping
from typing import Any

import httpx

from tgm.core.llm import (
    JsonSchema,
    build_chat_completions_request,
    check_input_budget,
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
        self._client = httpx.AsyncClient(timeout=request_timeout_seconds)
        self._lock = asyncio.Lock()

    async def call_json(
        self,
        system: str,
        user: str,
        schema: JsonSchema,
        max_input_tokens: int,
    ) -> dict:
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
            return await self._post_and_parse(
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

    async def _post_and_parse(
        self,
        *,
        url: str,
        headers: dict[str, str],
        request_body: dict[str, Any],
        prompt_chars: int,
        prompt_tokens_estimated: int,
    ) -> dict:
        started_at = time.monotonic()
        try:
            response = await self._client.post(url, json=request_body, headers=headers)
            response.raise_for_status()
            parsed = parse_chat_completions_response(response.json())
        except Exception:
            logger.error(
                "LLM call failed",
                extra={
                    "model": self._model,
                    "prompt_chars": prompt_chars,
                    "prompt_tokens_est": prompt_tokens_estimated,
                    "latency_ms": _ms_since(started_at),
                    "success": False,
                },
            )
            raise

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


def _ms_since(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)
