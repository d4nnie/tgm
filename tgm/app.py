from tgm.shell.db import connect, migrate, resolve_db_path
from tgm.shell.platform import ensure_user_data_dir


def main() -> None:
    ensure_user_data_dir()

    db_path = resolve_db_path()
    connection = connect(db_path)
    try:
        migrate(connection)
    finally:
        connection.close()
    print(f"DB ready at {db_path}")
