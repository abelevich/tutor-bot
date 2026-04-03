from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    telegram_id: int
    display_name: str | None = None
    native_language: str = "ru"
    target_language: str = "en"
    proficiency: str = "B2"
    profile_summary: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Conversation:
    id: int | None = None
    user_id: int = 0
    target_language: str = "en"
    mode: str = "chat"
    topic: str | None = None
    active: bool = True
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None


@dataclass
class Message:
    id: int | None = None
    conversation_id: int = 0
    role: str = ""  # user, assistant
    content_text: str | None = None
    corrections_json: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ErrorLogEntry:
    id: int | None = None
    user_id: int = 0
    message_id: int | None = None
    error_category: str | None = None
    original_text: str | None = None
    corrected_text: str | None = None
    explanation: str | None = None
    severity: str | None = None  # red, yellow, green
    created_at: datetime = field(default_factory=datetime.now)
