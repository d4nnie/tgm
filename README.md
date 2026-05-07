# Telegram Monitor

Personal desktop application for **Windows** and **Linux** that monitors
selected Telegram chats via [Telethon](https://docs.telethon.dev/) and
produces summaries plus highlighted-message digests through a local LLM
(default: [Ollama](https://ollama.com/) running `gpt-oss:20b`).
Importance criteria are learnt per-user from manual feedback and chat
profiles. Anthropic and OpenAI back-ends are pluggable alternatives.

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) — package and venv manager
- (Runtime) Telegram `api_id` / `api_hash` from
  [my.telegram.org](https://my.telegram.org). The first launch walks
  you through the auth flow.
- (Runtime, default LLM) [Ollama](https://ollama.com/) with the
  `gpt-oss:20b` model pulled. Cloud back-ends (Anthropic, OpenAI) are
  available as alternatives.

## Setup

```bash
git clone <this-repo>
cd tgm
uv sync
uv run pre-commit install
```

`uv sync` resolves the lockfile, builds the local package in editable
mode and installs both runtime and dev dependencies. `pre-commit
install` wires the project's checks into your local `git commit` hook.

## Run

```bash
uv run telegram-monitor              # CLI / GUI entry point
uv run telegram-monitor --help       # once subcommands land
```

The console-script `telegram-monitor` is registered via
`[project.scripts]` in `pyproject.toml`. Without arguments it launches
the GUI; subcommands run the CLI front-end.

## Develop

```bash
uv run ruff check .          # lint (E, W, F, I, UP, B, SIM, N)
uv run ruff format .         # format (Black-compatible)
uv run ty check .            # type check (Astral's ty)
uv run pre-commit run --all-files
```

The pre-commit hook runs all three checks on staged Python files and
blocks the commit on any failure. Versions are pinned through
`uv.lock`.

## Configuration and runtime data

- `api_id` / `api_hash` are loaded with a trinity-fallback:
  environment variables `TGM_API_ID` / `TGM_API_HASH`, then a local
  `config.toml` in the user data directory, then the first-launch
  wizard. Nothing is ever bundled into release artefacts.
- The SQLite database lives at `<user-data-dir>/db.sqlite`. The path
  resolves to `%APPDATA%\telegram-monitor\db.sqlite` on Windows and
  `$XDG_DATA_HOME/telegram-monitor/db.sqlite` on Linux. Override
  through `TGM_DB_PATH` for development.

## License

See [LICENSE](LICENSE).
