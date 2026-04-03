from __future__ import annotations

import json
import logging

from aiogram import Router
from aiogram.types import Message

from src.config import settings
from src.db.models import User
from src.db.repository import (
    create_conversation,
    get_active_conversation,
    log_error,
    save_message,
)
from src.tutor.correction import parse_error_details, parse_tutor_response
from src.tutor.engine import get_tutor_response
from src.tutor.languages import LanguageConfig
from src.utils.telegram import send_tutor_response

logger = logging.getLogger(__name__)

router = Router()


@router.message()
async def handle_text_message(
    message: Message,
    db_user: User | None = None,
    language_config: LanguageConfig | None = None,
) -> None:
    if not message.text or not message.from_user:
        return

    # User must be onboarded
    if db_user is None or language_config is None:
        await message.answer(
            "Please set up your profile first with /start"
        )
        return

    user_text = message.text.strip()
    if not user_text:
        return

    # Get or create active conversation
    conversation = await get_active_conversation(
        settings.database_path, db_user.telegram_id
    )
    if conversation is None:
        conversation = await create_conversation(
            settings.database_path,
            db_user.telegram_id,
            db_user.target_language,
        )

    # Save user message
    await save_message(
        settings.database_path,
        conversation.id,  # type: ignore[arg-type]
        "user",
        user_text,
    )

    # Get tutor response
    try:
        raw_response = await get_tutor_response(
            db_user, language_config, conversation.id, user_text  # type: ignore[arg-type]
        )
    except Exception:
        logger.exception("Error calling Claude API")
        await message.answer(
            "Sorry, I'm having trouble right now. Please try again in a moment."
        )
        return

    # Parse response
    tutor_response = parse_tutor_response(raw_response)

    # Save assistant message
    assistant_msg_id = await save_message(
        settings.database_path,
        conversation.id,  # type: ignore[arg-type]
        "assistant",
        tutor_response.raw,
        corrections_json=json.dumps(tutor_response.correction) if tutor_response.correction else None,
    )

    # Log errors to error_log table
    if tutor_response.correction:
        error_details = parse_error_details(tutor_response.correction)
        for detail in error_details:
            await log_error(
                settings.database_path,
                db_user.telegram_id,
                assistant_msg_id,
                error_category=detail.severity,
                original_text=detail.original,
                corrected_text=detail.corrected,
                explanation=detail.explanation,
                severity=detail.severity,
            )

    # Send response to user
    await send_tutor_response(message.bot, message.chat.id, tutor_response)  # type: ignore[arg-type]
