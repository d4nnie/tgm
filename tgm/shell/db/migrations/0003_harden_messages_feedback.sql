DELETE FROM messages WHERE chat_id NOT IN (SELECT chat_id FROM chats);
DELETE FROM feedback WHERE chat_id NOT IN (SELECT chat_id FROM chats);
UPDATE messages SET raw_json = '{}' WHERE raw_json IS NULL;

CREATE TABLE messages_new (
    chat_id         INTEGER NOT NULL REFERENCES chats(chat_id),
    msg_id          INTEGER NOT NULL,
    ts              TIMESTAMP NOT NULL,
    sender_id       INTEGER,
    sender_name     TEXT,
    text            TEXT,
    reply_to_msg_id INTEGER,
    edited_at       TIMESTAMP,
    raw_json        TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (chat_id, msg_id)
);
INSERT INTO messages_new (chat_id, msg_id, ts, sender_id, sender_name, text, reply_to_msg_id, edited_at, raw_json)
SELECT chat_id, msg_id, ts, sender_id, sender_name, text, reply_to_msg_id, edited_at, COALESCE(raw_json, '{}')
FROM messages;
DROP TABLE messages;
ALTER TABLE messages_new RENAME TO messages;
CREATE INDEX IF NOT EXISTS idx_messages_chat_ts ON messages(chat_id, ts);

CREATE TABLE feedback_new (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id      INTEGER NOT NULL REFERENCES chats(chat_id),
    msg_ids_json TEXT NOT NULL,
    user_comment TEXT,
    scope        TEXT NOT NULL,
    consumed     INTEGER NOT NULL DEFAULT 0,
    marked_at    TIMESTAMP NOT NULL
);
INSERT INTO feedback_new (id, chat_id, msg_ids_json, user_comment, scope, consumed, marked_at)
SELECT id, chat_id, msg_ids_json, user_comment, scope, consumed, marked_at
FROM feedback;
DROP TABLE feedback;
ALTER TABLE feedback_new RENAME TO feedback;
CREATE INDEX IF NOT EXISTS idx_feedback_scope_consumed_marked ON feedback(scope, consumed, marked_at);
