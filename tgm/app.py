from tgm.shell.db import connect, migrate, resolve_db_path


def main() -> None:
    db_path = resolve_db_path()
    connection = connect(db_path)
    try:
        migrate(connection)
    finally:
        connection.close()
    print(f"DB ready at {db_path}")
