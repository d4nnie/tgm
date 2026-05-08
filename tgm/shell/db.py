import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from tgm.shell.platform import get_user_data_dir

_DB_PATH_ENV_VAR = "TGM_DB_PATH"
_DB_FILENAME = "db.sqlite"

_SCHEMA_VERSION_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_SELECT_CURRENT_SCHEMA_VERSION = "SELECT COALESCE(MAX(version), 0) FROM schema_version"
_INSERT_SCHEMA_VERSION = "INSERT INTO schema_version(version) VALUES (?)"

_INITIAL_DDL = """
CREATE TABLE user_profile (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE chats (
    chat_id          INTEGER PRIMARY KEY,
    title            TEXT NOT NULL,
    type             TEXT NOT NULL,
    is_monitored     INTEGER NOT NULL DEFAULT 0,
    period_n_minutes INTEGER NOT NULL DEFAULT 30,
    added_at         TIMESTAMP NOT NULL
);

CREATE TABLE chat_profiles (
    chat_id            INTEGER PRIMARY KEY REFERENCES chats(chat_id),
    description_prompt TEXT NOT NULL DEFAULT '',
    rolling_summary    TEXT NOT NULL DEFAULT '',
    updated_at         TIMESTAMP NOT NULL
);

CREATE TABLE messages (
    chat_id         INTEGER NOT NULL,
    msg_id          INTEGER NOT NULL,
    ts              TIMESTAMP NOT NULL,
    sender_id       INTEGER,
    sender_name     TEXT,
    text            TEXT,
    reply_to_msg_id INTEGER,
    edited_at       TIMESTAMP,
    raw_json        TEXT,
    PRIMARY KEY (chat_id, msg_id)
);
CREATE INDEX idx_messages_chat_ts ON messages(chat_id, ts);

CREATE TABLE digests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scope           TEXT NOT NULL,
    chat_id         INTEGER,
    run_ts          TIMESTAMP NOT NULL,
    summary         TEXT NOT NULL,
    highlights_json TEXT NOT NULL,
    seen            INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_digests_scope_chat_ts ON digests(scope, chat_id, run_ts);

CREATE TABLE importance_criteria (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    scope         TEXT NOT NULL,
    criteria_text TEXT NOT NULL,
    version       INTEGER NOT NULL,
    updated_at    TIMESTAMP NOT NULL,
    UNIQUE (scope, version)
);

CREATE TABLE feedback (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id      INTEGER NOT NULL,
    msg_ids_json TEXT NOT NULL,
    user_comment TEXT,
    scope        TEXT NOT NULL,
    consumed     INTEGER NOT NULL DEFAULT 0,
    marked_at    TIMESTAMP NOT NULL
);

CREATE TABLE run_state (
    scope       TEXT PRIMARY KEY,
    last_run_at TIMESTAMP,
    last_msg_id INTEGER
);
"""

_MIGRATIONS: list[tuple[int, str]] = [
    (1, _INITIAL_DDL),
]


@dataclass(frozen=True)
class DatabaseHandle:
    engine: Engine
    session_factory: sessionmaker[Session]


def resolve_db_path() -> Path:
    override = os.environ.get(_DB_PATH_ENV_VAR)
    if override:
        return Path(override)
    return get_user_data_dir() / _DB_FILENAME


def open_database() -> DatabaseHandle:
    db_path = resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{db_path}")
    _attach_pragmas(engine)

    return DatabaseHandle(
        engine=engine,
        session_factory=sessionmaker(engine, expire_on_commit=False),
    )


def apply_migrations(engine: Engine) -> None:
    raw_connection = engine.raw_connection()
    try:
        cursor = raw_connection.cursor()
        cursor.executescript(_SCHEMA_VERSION_TABLE_DDL)
        current = cursor.execute(_SELECT_CURRENT_SCHEMA_VERSION).fetchone()[0]
        for version, sql in _MIGRATIONS:
            if version <= current:
                continue
            cursor.executescript(sql)
            cursor.execute(_INSERT_SCHEMA_VERSION, (version,))
        raw_connection.commit()
    finally:
        raw_connection.close()


def _attach_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # ty: ignore[unresolved-attribute]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
