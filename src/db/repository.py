from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from src.db.models import Conversation, ErrorLogEntry, Message, User

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id     INTEGER PRIMARY KEY,
    display_name    TEXT,
    native_language TEXT DEFAULT 'ru',
    target_language TEXT DEFAULT 'en',
    proficiency     TEXT DEFAULT 'B2',
    profile_summary TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(telegram_id),
    target_language TEXT,
    mode            TEXT DEFAULT 'chat',
    topic           TEXT,
    active          BOOLEAN DEFAULT 1,
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at        TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER REFERENCES conversations(id),
    role            TEXT NOT NULL,
    content_text    TEXT,
    corrections_json TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS error_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(telegram_id),
    message_id      INTEGER REFERENCES messages(id),
    error_category  TEXT,
    original_text   TEXT,
    corrected_text  TEXT,
    explanation     TEXT,
    severity        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_error_log_user ON error_log(user_id, error_category, created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_active ON conversations(user_id, active);
"""


async def setup_db(db_path: str) -> None:
    """Create tables and indexes if they don't exist."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


async def _get_db(db_path: str) -> aiosqlite.Connection:
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db


# ── Users ────────────────────────────────────────────────────────────

async def create_user(db_path: str, telegram_id: int) -> User:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
            (telegram_id,),
        )
        await db.commit()
    return await get_user(db_path, telegram_id)  # type: ignore[return-value]


async def get_user(db_path: str, telegram_id: int) -> User | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return User(
            telegram_id=row["telegram_id"],
            display_name=row["display_name"],
            native_language=row["native_language"],
            target_language=row["target_language"],
            proficiency=row["proficiency"],
            profile_summary=row["profile_summary"],
        )


async def upsert_user(
    db_path: str,
    telegram_id: int,
    display_name: str | None = None,
    native_language: str | None = None,
    target_language: str | None = None,
    proficiency: str | None = None,
) -> User:
    user = await get_user(db_path, telegram_id)
    if user is None:
        user = await create_user(db_path, telegram_id)

    updates: list[str] = []
    params: list[object] = []
    if display_name is not None:
        updates.append("display_name = ?")
        params.append(display_name)
    if native_language is not None:
        updates.append("native_language = ?")
        params.append(native_language)
    if target_language is not None:
        updates.append("target_language = ?")
        params.append(target_language)
    if proficiency is not None:
        updates.append("proficiency = ?")
        params.append(proficiency)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(telegram_id)
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE telegram_id = ?",
                params,
            )
            await db.commit()

    return await get_user(db_path, telegram_id)  # type: ignore[return-value]


async def update_user_language(
    db_path: str, telegram_id: int, target_language: str
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE users SET target_language = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?",
            (target_language, telegram_id),
        )
        await db.commit()


# ── Conversations ────────────────────────────────────────────────────

async def create_conversation(
    db_path: str, user_id: int, target_language: str
) -> Conversation:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "INSERT INTO conversations (user_id, target_language) VALUES (?, ?)",
            (user_id, target_language),
        )
        await db.commit()
        return Conversation(
            id=cursor.lastrowid,
            user_id=user_id,
            target_language=target_language,
        )


async def get_active_conversation(
    db_path: str, user_id: int
) -> Conversation | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM conversations WHERE user_id = ? AND active = 1 ORDER BY started_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return Conversation(
            id=row["id"],
            user_id=row["user_id"],
            target_language=row["target_language"],
            mode=row["mode"],
            topic=row["topic"],
            active=bool(row["active"]),
        )


async def end_conversation(db_path: str, conversation_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE conversations SET active = 0, ended_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        await db.commit()


async def end_all_conversations(db_path: str, user_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE conversations SET active = 0, ended_at = CURRENT_TIMESTAMP WHERE user_id = ? AND active = 1",
            (user_id,),
        )
        await db.commit()


# ── Messages ─────────────────────────────────────────────────────────

async def save_message(
    db_path: str,
    conversation_id: int,
    role: str,
    content_text: str,
    corrections_json: str | None = None,
) -> int:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "INSERT INTO messages (conversation_id, role, content_text, corrections_json) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content_text, corrections_json),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]


async def get_recent_messages(
    db_path: str, conversation_id: int, limit: int = 20
) -> list[Message]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM (SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?) ORDER BY created_at ASC",
            (conversation_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content_text=row["content_text"],
                corrections_json=row["corrections_json"],
            )
            for row in rows
        ]


# ── Error log ────────────────────────────────────────────────────────

async def log_error(
    db_path: str,
    user_id: int,
    message_id: int | None,
    error_category: str | None,
    original_text: str | None,
    corrected_text: str | None,
    explanation: str | None,
    severity: str | None,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO error_log (user_id, message_id, error_category, original_text, corrected_text, explanation, severity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, message_id, error_category, original_text, corrected_text, explanation, severity),
        )
        await db.commit()
