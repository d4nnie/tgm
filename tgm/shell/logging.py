import logging
import logging.handlers
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from tgm.core.logging_filter import is_field_allowed

_LOG_FILENAME = "app.log"
_FILE_HANDLER_MAX_BYTES = 10 * 1024 * 1024
_FILE_HANDLER_BACKUP_COUNT = 3

_TGM_LOGGER_NAME = "tgm"
_THIRD_PARTY_LOGGER_NAMES = ("telethon", "httpx", "sqlalchemy.engine")

_REDACTION_PLACEHOLDER = "<redacted>"

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

_PYDANTIC_INPUT_VALUE_PATTERN = re.compile(r"input_value=.*?(?=,\s*input_type|$)", flags=re.DOTALL)
_HTTPX_RESPONSE_PATTERN = re.compile(r"response:.*$", flags=re.DOTALL)


class TgmPiiFilter(logging.Filter):
    def __init__(self, redact: bool) -> None:
        super().__init__()
        self.redact = redact

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.redact:
            return True
        for field_name in list(record.__dict__.keys()):
            if field_name in _RESERVED_LOG_RECORD_ATTRIBUTES or field_name.startswith("_"):
                continue
            if not is_field_allowed(field_name):
                record.__dict__[field_name] = _REDACTION_PLACEHOLDER
        return True


class KeyValueFormatter(logging.Formatter):
    def __init__(self, *, redact_tracebacks: bool) -> None:
        super().__init__()
        self._redact_tracebacks = redact_tracebacks

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        head = f"{timestamp} [{record.name}] {record.levelname} {record.getMessage()}"

        extras = _render_extra_fields(record)
        if extras:
            head = f"{head} {extras}"
        if record.exc_info:
            head = f"{head}\n{self.formatException(record.exc_info)}"
        return head

    def formatException(self, ei) -> str:  # noqa: N802, ANN001  # logging.Formatter API name
        raw = super().formatException(ei)
        if not self._redact_tracebacks:
            return raw
        raw = _PYDANTIC_INPUT_VALUE_PATTERN.sub("input_value=<redacted>", raw)
        raw = _HTTPX_RESPONSE_PATTERN.sub("response: <redacted>", raw)
        return raw


def setup_logging(user_data_dir: Path, *, debug_pii: bool = False) -> None:
    formatter = KeyValueFormatter(redact_tracebacks=not debug_pii)
    pii_filter = TgmPiiFilter(redact=not debug_pii)

    handlers = [
        _build_rotating_file_handler(user_data_dir / _LOG_FILENAME, formatter),
        _build_stderr_handler(formatter),
    ]

    _install_root_handlers(handlers, level=logging.INFO)
    _attach_pii_filter_to_tgm_namespace(pii_filter)
    _quiet_third_party_loggers()


def _build_rotating_file_handler(
    log_path: Path,
    formatter: logging.Formatter,
) -> logging.Handler:
    handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=_FILE_HANDLER_MAX_BYTES,
        backupCount=_FILE_HANDLER_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler


def _build_stderr_handler(formatter: logging.Formatter) -> logging.Handler:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(formatter)
    return handler


def _install_root_handlers(handlers: list[logging.Handler], level: int) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for existing_handler in list(root_logger.handlers):
        root_logger.removeHandler(existing_handler)
    for handler in handlers:
        root_logger.addHandler(handler)


def _attach_pii_filter_to_tgm_namespace(pii_filter: logging.Filter) -> None:
    tgm_logger = logging.getLogger(_TGM_LOGGER_NAME)
    for existing in list(tgm_logger.filters):
        if isinstance(existing, TgmPiiFilter):
            tgm_logger.removeFilter(existing)
    tgm_logger.addFilter(pii_filter)


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
