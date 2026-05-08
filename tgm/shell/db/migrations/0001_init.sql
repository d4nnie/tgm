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
