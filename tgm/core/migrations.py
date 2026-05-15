def compose_atomic_migration(sql: str, version: int) -> str:
    return f"BEGIN;\n{sql}\nINSERT INTO schema_version(version) VALUES ({version});\nCOMMIT;"
