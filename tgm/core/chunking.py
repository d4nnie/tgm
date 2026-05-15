from dataclasses import replace

from tgm.core.prompts import render_message
from tgm.core.tokens import estimate_tokens
from tgm.core.types import Message, PerChatDigestPart


def split_into_chunks(
    messages: list[Message],
    *,
    max_messages_per_chunk: int,
    max_tokens_per_chunk: int,
) -> list[list[Message]]:
    if not messages:
        return []
    chunks: list[list[Message]] = []
    current: list[Message] = []
    current_tokens = 0
    for message in messages:
        current, current_tokens = _absorb_message(
            chunks, current, current_tokens, message, max_messages_per_chunk, max_tokens_per_chunk
        )
    if current:
        chunks.append(current)
    return chunks


def _absorb_message(
    chunks: list[list[Message]],
    current: list[Message],
    current_tokens: int,
    message: Message,
    max_messages: int,
    max_tokens: int,
) -> tuple[list[Message], int]:
    message_tokens = estimate_tokens(render_message(message))
    if _should_flush(current, current_tokens, message_tokens, max_messages, max_tokens):
        chunks.append(current)
        current, current_tokens = [], 0
    current.append(message)
    return current, current_tokens + message_tokens


def _should_flush(
    current: list[Message],
    current_tokens: int,
    extra_tokens: int,
    max_messages: int,
    max_tokens: int,
) -> bool:
    if not current:
        return False
    return _would_exceed_limits(
        current_count=len(current),
        current_tokens=current_tokens,
        extra_tokens=extra_tokens,
        max_messages=max_messages,
        max_tokens=max_tokens,
    )


def trim_to_budget(
    digest_parts: list[PerChatDigestPart],
    *,
    max_tokens: int,
) -> list[PerChatDigestPart]:
    parts = list(digest_parts)
    total = _estimate_parts_tokens(parts)
    while total > max_tokens:
        candidates = [index for index, part in enumerate(parts) if part.highlights]
        # Never strip the newest part's highlights — the freshest signal stays.
        if len(candidates) <= 1:
            return parts
        oldest = candidates[0]
        oldest_highlights = parts[oldest].highlights
        stripped = sum(estimate_tokens(highlight.why) for highlight in oldest_highlights)
        parts[oldest] = replace(parts[oldest], highlights=())
        total -= stripped
    return parts


def _would_exceed_limits(
    *,
    current_count: int,
    current_tokens: int,
    extra_tokens: int,
    max_messages: int,
    max_tokens: int,
) -> bool:
    if current_count + 1 > max_messages:
        return True
    return current_tokens + extra_tokens > max_tokens


def _estimate_parts_tokens(parts: list[PerChatDigestPart]) -> int:
    total = 0
    for part in parts:
        total += estimate_tokens(part.summary)
        for highlight in part.highlights:
            total += estimate_tokens(highlight.why)
    return total
