import sqlite3
from datetime import datetime

from tgm.core.types import Chat, ChatType, Message

_INSERT_MESSAGE_SQL = """
INSERT OR IGNORE INTO messages (
    chat_id, msg_id, ts, sender_id, sender_name, text, reply_to_msg_id, edited_at, raw_json
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_UPDATE_MESSAGE_EDIT_SQL = """
UPDATE messages
SET text = ?, edited_at = ?, raw_json = ?
WHERE chat_id = ? AND msg_id = ?
"""

_UPSERT_CHAT_SQL = """
INSERT INTO chats (chat_id, title, type, is_monitored, period_n_minutes, added_at)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(chat_id) DO UPDATE SET
    title = excluded.title,
    type = excluded.type,
    is_monitored = excluded.is_monitored,
    period_n_minutes = excluded.period_n_minutes
"""

_MARK_CHAT_UNMONITORED_SQL = "UPDATE chats SET is_monitored = 0 WHERE chat_id = ?"

_SELECT_IS_CHAT_MONITORED_SQL = "SELECT is_monitored FROM chats WHERE chat_id = ?"

_SELECT_MONITORED_CHAT_IDS_SQL = "SELECT chat_id FROM chats WHERE is_monitored = 1"

_SELECT_CHATS_SQL = """
SELECT chat_id, title, type, is_monitored, period_n_minutes, added_at
FROM chats
ORDER BY title
"""


def insert_message(connection: sqlite3.Connection, message: Message) -> None:
    connection.execute(
        _INSERT_MESSAGE_SQL,
        (
            message.chat_id,
            message.msg_id,
            message.timestamp.isoformat(),
            message.sender_id,
            message.sender_name,
            message.text,
            message.reply_to_msg_id,
            message.edited_at.isoformat() if message.edited_at else None,
            message.raw_json,
        ),
    )


def update_message_edit(
    connection: sqlite3.Connection,
    *,
    chat_id: int,
    msg_id: int,
    text: str | None,
    edited_at: datetime,
    raw_json: str,
) -> None:
    connection.execute(
        _UPDATE_MESSAGE_EDIT_SQL,
        (text, edited_at.isoformat(), raw_json, chat_id, msg_id),
    )


def upsert_chat(connection: sqlite3.Connection, chat: Chat) -> None:
    connection.execute(
        _UPSERT_CHAT_SQL,
        (
            chat.chat_id,
            chat.title,
            chat.chat_type,
            int(chat.is_monitored),
            chat.period_n_minutes,
            chat.added_at.isoformat(),
        ),
    )


def mark_chat_unmonitored(connection: sqlite3.Connection, chat_id: int) -> None:
    connection.execute(_MARK_CHAT_UNMONITORED_SQL, (chat_id,))


def is_chat_monitored(connection: sqlite3.Connection, chat_id: int) -> bool:
    row = connection.execute(_SELECT_IS_CHAT_MONITORED_SQL, (chat_id,)).fetchone()
    if row is None:
        return False
    return bool(row[0])


def list_monitored_chat_ids(connection: sqlite3.Connection) -> list[int]:
    rows = connection.execute(_SELECT_MONITORED_CHAT_IDS_SQL).fetchall()
    return [int(row[0]) for row in rows]


def list_chats(connection: sqlite3.Connection) -> list[Chat]:
    rows = connection.execute(_SELECT_CHATS_SQL).fetchall()
    return [_row_to_chat(row) for row in rows]


def _row_to_chat(row: tuple) -> Chat:
    chat_type: ChatType = row[2]
    return Chat(
        chat_id=int(row[0]),
        title=str(row[1]),
        chat_type=chat_type,
        is_monitored=bool(row[3]),
        period_n_minutes=int(row[4]),
        added_at=datetime.fromisoformat(str(row[5])),
    )
