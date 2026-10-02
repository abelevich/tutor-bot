from __future__ import annotations

import litellm

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
    """Call the configured LLM via LiteLLM and return the raw response text."""
    system_prompt, messages = await build_context(
        user, language_config, conversation_id
    )

    messages.append({"role": "user", "content": user_text})

    response = await litellm.acompletion(
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
        messages=[{"role": "system", "content": system_prompt}, *messages],
        api_key=settings.llm_api_key or None,
        api_base=settings.llm_api_base or None,
    )

    return response.choices[0].message.content or ""  # type: ignore[union-attr]
