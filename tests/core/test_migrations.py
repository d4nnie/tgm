from tgm.core.migrations import compose_atomic_migration


def test_compose_atomic_migration_wraps_in_begin_commit():
    result = compose_atomic_migration("CREATE TABLE x(a);", 1)

    assert result.startswith("BEGIN;")
    assert result.endswith("COMMIT;")


def test_compose_atomic_migration_includes_original_sql():
    result = compose_atomic_migration("CREATE TABLE x(a);", 1)

    assert "CREATE TABLE x(a);" in result


def test_compose_atomic_migration_includes_schema_version_insert():
    result = compose_atomic_migration("CREATE TABLE x(a);", 7)

    assert "INSERT INTO schema_version(version) VALUES (7);" in result


def test_compose_atomic_migration_orders_segments_correctly():
    result = compose_atomic_migration("CREATE TABLE x(a);", 3)

    begin_index = result.index("BEGIN;")
    sql_index = result.index("CREATE TABLE x(a);")
    insert_index = result.index("INSERT INTO schema_version(version) VALUES (3);")
    commit_index = result.index("COMMIT;")

    assert begin_index < sql_index < insert_index < commit_index
