_ALLOWED_EXTRA_FIELDS: frozenset[str] = frozenset(
    {
        "attempt",
        "attempts",
        "category",
        "chat_id",
        "chats",
        "command",
        "count",
        "error_type",
        "feedback_count",
        "http_status",
        "inserted",
        "inserted_count",
        "latency_ms",
        "lock_path",
        "message_id",
        "model",
        "mutex",
        "new_version",
        "old_version",
        "prompt_chars",
        "prompt_tokens_est",
        "reason",
        "rolled_back_to",
        "scope",
        "since_message_id",
        "sleep_seconds",
        "status",
        "success",
        "version",
        "wait_seconds",
    }
)


def is_field_allowed(field_name: str) -> bool:
    return field_name in _ALLOWED_EXTRA_FIELDS
