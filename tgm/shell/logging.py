import logging
import logging.handlers
import sys
from datetime import UTC, datetime
from pathlib import Path

_LOG_FILENAME = "app.log"
_FILE_HANDLER_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_FILE_HANDLER_BACKUP_COUNT = 3

_THIRD_PARTY_LOGGER_NAMES = ("telethon", "httpx", "sqlalchemy.engine")

# Field names redacted by default — PII per NFR-SEC-3. Keep minimal here;
# real list expands with EPIC-07/08 when message/highlight pipelines log.
_PII_REDACTED_FIELDS = frozenset(
    {
        "text",
        "sender_name",
        "user_comment",
        "prompt",
        "raw_json",
    }
)
_PII_REDACTION_PLACEHOLDER = "<redacted>"

_RESERVED_LOG_RECORD_ATTRIBUTES = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class PIIRedactionFilter(logging.Filter):
    def __init__(self, redact: bool) -> None:
        super().__init__()
        self.redact = redact

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.redact:
            return True
        for field_name in _PII_REDACTED_FIELDS:
            if field_name in record.__dict__:
                record.__dict__[field_name] = _PII_REDACTION_PLACEHOLDER
        return True


class KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        head = f"{timestamp} [{record.name}] {record.levelname} {record.getMessage()}"

        extras = _render_extra_fields(record)
        if extras:
            head = f"{head} {extras}"
        if record.exc_info:
            head = f"{head}\n{self.formatException(record.exc_info)}"
        return head


def setup_logging(user_data_dir: Path, *, debug_pii: bool = False) -> None:
    formatter = KeyValueFormatter()
    pii_filter = PIIRedactionFilter(redact=not debug_pii)

    handlers = [
        _build_rotating_file_handler(user_data_dir / _LOG_FILENAME, formatter, pii_filter),
        _build_stderr_handler(formatter, pii_filter),
    ]

    _install_root_handlers(handlers, level=logging.INFO)
    _quiet_third_party_loggers()


def _build_rotating_file_handler(
    log_path: Path,
    formatter: logging.Formatter,
    pii_filter: logging.Filter,
) -> logging.Handler:
    handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=_FILE_HANDLER_MAX_BYTES,
        backupCount=_FILE_HANDLER_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.addFilter(pii_filter)
    return handler


def _build_stderr_handler(
    formatter: logging.Formatter,
    pii_filter: logging.Filter,
) -> logging.Handler:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(formatter)
    handler.addFilter(pii_filter)
    return handler


def _install_root_handlers(handlers: list[logging.Handler], level: int) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for existing_handler in list(root_logger.handlers):
        root_logger.removeHandler(existing_handler)
    for handler in handlers:
        root_logger.addHandler(handler)


def _quiet_third_party_loggers() -> None:
    for logger_name in _THIRD_PARTY_LOGGER_NAMES:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def _render_extra_fields(record: logging.LogRecord) -> str:
    parts: list[str] = []
    for key, value in record.__dict__.items():
        if key in _RESERVED_LOG_RECORD_ATTRIBUTES or key.startswith("_"):
            continue
        parts.append(f"{key}={_quote_value(value)}")
    return " ".join(parts)


def _quote_value(value: object) -> str:
    text = str(value)
    if not text or any(character.isspace() for character in text) or '"' in text or "=" in text:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text
