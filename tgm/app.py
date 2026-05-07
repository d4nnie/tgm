from tgm.shell.db import connect, migrate, resolve_db_path


def main() -> None:
    db_path = resolve_db_path()
    conn = connect(db_path)
    try:
        migrate(conn)
    finally:
        conn.close()
    print(f"DB ready at {db_path}")
