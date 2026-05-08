from dataclasses import replace

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
        message_tokens = estimate_tokens(_render_for_estimate(message))
        if current and _would_exceed_limits(
            current_count=len(current),
            current_tokens=current_tokens,
            extra_tokens=message_tokens,
            max_messages=max_messages_per_chunk,
            max_tokens=max_tokens_per_chunk,
        ):
            chunks.append(current)
            current = []
            current_tokens = 0
        current.append(message)
        current_tokens += message_tokens

    if current:
        chunks.append(current)
    return chunks


def trim_to_budget(
    digest_parts: list[PerChatDigestPart],
    *,
    max_tokens: int,
) -> list[PerChatDigestPart]:
    parts = list(digest_parts)
    while _estimate_parts_tokens(parts) > max_tokens:
        candidates = [index for index, part in enumerate(parts) if part.highlights]
        # Never strip the newest part's highlights — the freshest signal stays.
        if len(candidates) <= 1:
            return parts
        oldest = candidates[0]
        parts[oldest] = replace(parts[oldest], highlights=[])
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


def _render_for_estimate(message: Message) -> str:
    sender = message.sender_name or "unknown"
    text = message.text if message.text is not None else "<no text>"
    return f"[message_id={message.message_id}] {sender} ({message.timestamp.isoformat()}): {text}"


def _estimate_parts_tokens(parts: list[PerChatDigestPart]) -> int:
    total = 0
    for part in parts:
        total += estimate_tokens(part.summary)
        for highlight in part.highlights:
            total += estimate_tokens(highlight.why)
    return total
