import logging
import os
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from tgm.core.migrations import compose_atomic_migration
from tgm.shell.platform import get_user_data_dir

logger = logging.getLogger(__name__)

_DB_PATH_ENV_VAR = "TGM_DB_PATH"
_DB_FILENAME = "db.sqlite"

_MIGRATIONS_PACKAGE = "tgm.shell.db.migrations"
_MIGRATION_FILENAME_SUFFIX = ".sql"

_SCHEMA_VERSION_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_SELECT_CURRENT_SCHEMA_VERSION = "SELECT COALESCE(MAX(version), 0) FROM schema_version"


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
    migrations = _load_migrations()
    raw_connection = engine.raw_connection()
    try:
        _apply_migrations_on_connection(raw_connection, migrations)
    finally:
        raw_connection.close()


def _apply_migrations_on_connection(raw_connection: object, migrations: list[tuple[int, str]]) -> None:
    cursor = raw_connection.cursor()  # ty: ignore[unresolved-attribute]
    cursor.executescript(_SCHEMA_VERSION_TABLE_DDL)
    current_version = cursor.execute(_SELECT_CURRENT_SCHEMA_VERSION).fetchone()[0]
    applied_count = _apply_pending_migrations(cursor, migrations, current_version)
    raw_connection.commit()  # ty: ignore[unresolved-attribute]
    if applied_count == 0:
        logger.info("Database schema is up to date", extra={"version": current_version})


def _apply_pending_migrations(cursor: object, migrations: list[tuple[int, str]], current_version: int) -> int:  # noqa: WPS221  # parameterised-type signature
    applied_count = 0
    for version, sql_text in migrations:
        if version <= current_version:
            continue
        atomic_sql = compose_atomic_migration(sql_text, version)
        cursor.executescript(atomic_sql)  # ty: ignore[unresolved-attribute]
        logger.info("Applied migration", extra={"version": version})
        applied_count += 1
    return applied_count


def _load_migrations() -> list[tuple[int, str]]:
    package_root = files(_MIGRATIONS_PACKAGE)
    migrations: list[tuple[int, str]] = []

    for resource in package_root.iterdir():
        filename = resource.name
        if not filename.endswith(_MIGRATION_FILENAME_SUFFIX):
            continue
        version_prefix, _, _ = filename.partition("_")
        version = int(version_prefix)
        sql_text = resource.read_text(encoding="utf-8")
        migrations.append((version, sql_text))

    migrations.sort(key=lambda entry: entry[0])
    return migrations


def _attach_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # ty: ignore[unresolved-attribute]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        # 5s cap when waiting on a write-write conflict; SQLite retries internally.
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
