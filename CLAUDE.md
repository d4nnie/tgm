# Telegram Monitor — Code Style Guide

Сквозной принцип: код должен быть **простым** и **тестируемым**. Никаких DI-контейнеров, никаких абстрактных интерфейсов «на будущее», никаких слоёв сверх Functional Core & Imperative Shell.

## Тулинг

- Python 3.11+. `requires-python = ">=3.11"`.
- `uv` — единственный пакетный менеджер. `uv.lock` коммитится. Запуск — через `uv run …`.
- `ruff` — линтер: `E`, `W`, `F`, `I`, `UP`, `B`, `SIM`, `N`, `S101`. Локальные исключения — только `# noqa: <code>` с краткой причиной.
- `ruff format` — форматтер. Длина строки 88.
- `ty` — primary type checker. Временный fallback на `mypy --strict` допустим.
- `pre-commit` хуки (`ruff check`, `ruff format --check`, `ty check`) обязаны проходить. Без `--no-verify`.

## Именование

- PEP 8 строго: `snake_case` для функций / переменных, `PascalCase` для классов, `UPPER_SNAKE` для констант.
- Модули и пакеты — all-lowercase, без подчёркиваний. ✅ `prompts.py`, `mainwindow.py`, `chatsettings.py`. ❌ `prompt_builders.py`, `main_window.py`, `per_chat_settings.py`. Если короткое слитное имя нечитаемо — переименуй понятие.
- Функции и методы начинаются с глагола. Исключение — `@property`-методы (могут быть существительными). ✅ `build_prompt`, `compute_tokens`, `is_due`, `has_highlights`. ❌ `prompt_builder`, `token_count`, `digest_pipeline`.
- Никаких двойных подчёркиваний в собственном коде: ни `__attr` (name mangling), ни custom dunder-методов. Стандартные dunder'ы языка (`__init__`, `__repr__`, `__eq__`, `__enter__`, `__hash__`) — можно. Приватность — одинарным `_`.
- Никаких сокращений в идентификаторах. `connection`, не `conn`. `message`, не `msg`. `request`, не `req`. `database`, не `db` для переменной. Исключения — устоявшиеся имена: `chat_id`, `msg_id`, `raw_json`, `idx_*`, `id`; имя модуля `shell/db.py`; имя функции `connect`.

## Типизация

- Приватные функции / методы (`_foo`, `Cls._method`) аннотируются полностью — параметры и возвращаемый тип.
- Публичные / локальные функции аннотируются ровно настолько, насколько нужно type checker'у. Параметры почти всегда аннотируются; возвращаемый тип нередко можно опустить.
- `X | None`, не `Optional[X]`. `list` / `dict` / `tuple`, не `List` / `Dict` / `Tuple`.

## Структура кода

- Без docstring'ов по умолчанию. Имя и типы документируют функцию. Однострочный комментарий допустим, только если **WHY** действительно неочевиден (скрытый инвариант, обход бага, неожиданное поведение). Не описывай **WHAT**.
- Без комментариев, если их удаление не сделает код менее понятным.
- Декомпозируй длинные функции. Если оркестратор разрастается (≈20+ строк, несколько фаз setup'а) — выноси шаги в именованные helpers, а сама функция остаётся коротким списком вызовов.
- Пустые строки внутри функции — скупо, только на границе **фаз работы**. Последовательные setup-операции — одна фаза, без пробелов внутри. Перед `return` — не вставлять. Если сомневаешься — пустая строка не нужна.

## Архитектура

`tgm/core/` — чистые синхронные функции `(данные) -> данные`. Никакого I/O, `async`, изменяемого состояния, `datetime.now()`. Время и прочее окружение — аргументом. Сигнатуры — на `dataclass` / `TypedDict` / примитивах; никаких ORM-объектов, Telethon-объектов, виджетов.

`tgm/shell/`, `tgm/cli/`, `tgm/ui/` — взаимодействие с миром: достали данные → передали в ядро → положили результат обратно. Бизнес-логика тут не пишется. Shell-модули конструируются явно в `app.py` и пробрасываются обычными аргументами — без DI-контейнеров и фабрик. Платформо-специфичный код — в `shell/platform/` с per-OS реализациями за общим контрактом.

## Ошибки

- `assert` запрещён в production-коде (всё под `tgm/`). `ruff S101` это enforce'ит. `assert` срезается под `python -O`.
- Вместо ассерта: `if condition: raise SomeError("message")`. Никакого `raise AssertionError(...)`.
- Для ветки «не должно случиться» — domain-specific подкласс `RuntimeError`, уже определённый в соответствующем модуле. Не вводи `RuntimeError` напрямую.
- Domain-exception'ы кладутся в `tgm/core/<module>.py` рядом с FSM/логикой, которую охраняют. Имя — `<Domain>Error`, базовый класс — `RuntimeError`.
- При сужении `X | None` → `X` — локализуй значение, проверь, кидай явный `raise`. Не используй inline-`assert`:

  ```python
  value = obj.field
  if value is None:
      raise SomeError("field must be set")
  use(value)
  ```

- Внешние ошибки (сеть / Telegram / Ollama) показываются пользователю человекочитаемо, не дампом исключения.

## Тестирование

- Юнит-тесты покрывают **исключительно `tgm/core/`**. Никаких mock'ов, никакого asyncio, никаких фикстур БД — данные на вход, assert на выход.
- Тесты для `shell/` не пишутся. Папка `tests/shell/` не создаётся. Корректность shell проверяется ручными E2E + ruff + ty. Если что-то нужно протестировать в shell — вынеси чистую логику в `core/` и протестируй её там.
- Запуск — `uv run pytest`. Расположение — `tests/core/`.
- Только плоские функции `def test_*():` — никаких `class Test...:`, никакого `unittest.TestCase`. Группировка — через префиксы в именах (`test_extract_from_env_*`, `test_merge_credentials_*`).
- В тестах `assert` идиоматичен и разрешён.
- Имя теста описывает кейс: `test_build_message_treats_empty_text_as_none` — docstring не нужен.

## Логирование

- Только stdlib `logging`. Никаких `loguru` / `structlog` / `picologging`.
- Root-logger проекта — `tgm`. В каждом модуле — `logger = logging.getLogger(__name__)`. Все handlers и filters навешиваются на root в `shell/logging.py::setup_logging()`. Модульные логгеры — `propagate=True`, без собственных handlers.
- Сообщения — английская проза с заглавной буквы: `"Applied migration"`, `"Retrying after Telegram error"`. Никаких snake_case event-токенов (`migration_applied`, `telethon_retry`).
- Структурированные поля — в `extra={...}`: `extra={"version": 1}`, `extra={"attempt": 0, "sleep_seconds": 60}`. KV-formatter добьёт их после прозы: `... INFO Applied migration version=1`.
- PII не логируется без явного `--debug-pii`. Только метаданные: `chat_id`, `msg_id`, размеры, latency, success. Тексты сообщений, имена, тела промптов — нет.
- При смене состояния backoff'а — одна запись на смену, не на каждый ретрай.

## Секреты

- `api_id` / `api_hash` загружаются по trinity-fallback: `TGM_API_ID` / `TGM_API_HASH` → `<user-data-dir>/config.toml` → wizard / `auth login`.
- `api_id` никогда не зашивается в бинарь — ни в коде, ни через build-time injection.
- В коммиты не попадают: `config.toml`, `*.session`, `.env`, `.envrc`.
- HTTP-клиент LLM ходит только на адреса, явно поддержанные провайдером: Ollama → `127.0.0.1` / `localhost` (или явно сконфигурированный LAN), Anthropic → `api.anthropic.com`, OpenAI → `api.openai.com`. Произвольные URL отклоняются на валидации конфига.

## Сборка

- Среда разработки — Linux. `.exe` локально не собираем — только в CI.
- Таргеты — Windows 10/11 x86_64 и Linux x86_64 (glibc 2.31+). macOS — out of scope.
- Сборка — на нативных GitHub Actions runner'ах: `ubuntu-latest` → `.AppImage`, `windows-latest` → `.exe`. Wine не используется.
