from __future__ import annotations

from src.config import settings
from src.db.models import User
from src.db.repository import get_recent_messages
from src.tutor.languages import LanguageConfig
from src.tutor.prompts import build_system_prompt


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: word count × 1.3."""
    return int(len(text.split()) * 1.3)


async def build_context(
    user: User,
    language_config: LanguageConfig,
    conversation_id: int,
) -> tuple[str, list[dict[str, str]]]:
    """Build system prompt and message history for the Anthropic API.

    Returns:
        (system_prompt, messages) where messages is a list of
        {"role": "user"|"assistant", "content": "..."} dicts.
    """
    system_prompt = build_system_prompt(user, language_config)

    raw_messages = await get_recent_messages(
        settings.database_path,
        conversation_id,
        limit=settings.max_context_messages,
    )

    messages: list[dict[str, str]] = []
    total_tokens = _estimate_tokens(system_prompt)

    for msg in raw_messages:
        if not msg.content_text:
            continue
        msg_tokens = _estimate_tokens(msg.content_text)
        if total_tokens + msg_tokens > settings.max_context_tokens:
            break
        messages.append({"role": msg.role, "content": msg.content_text})
        total_tokens += msg_tokens

    return system_prompt, messages
