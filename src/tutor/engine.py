from __future__ import annotations

import anthropic

from src.config import settings
from src.db.models import User
from src.tutor.context import build_context
from src.tutor.languages import LanguageConfig


async def get_tutor_response(
    user: User,
    language_config: LanguageConfig,
    conversation_id: int,
    user_text: str,
) -> str:
    """Call Claude API and return the raw response text."""
    system_prompt, messages = await build_context(
        user, language_config, conversation_id
    )

    messages.append({"role": "user", "content": user_text})

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=messages,  # type: ignore[arg-type]
    )

    return response.content[0].text  # type: ignore[union-attr]
