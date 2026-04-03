from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from src.config import settings
from src.db.repository import get_user
from src.tutor.languages import LANGUAGES, get_language


class UserMiddleware(BaseMiddleware):
    """Load user from DB and attach user + LanguageConfig to handler context."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_id: int | None = None
        if isinstance(event, Message) and event.from_user:
            telegram_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            telegram_id = event.from_user.id

        if telegram_id is not None:
            user = await get_user(settings.database_path, telegram_id)
            if user is not None:
                data["db_user"] = user
                try:
                    data["language_config"] = get_language(user.target_language)
                except KeyError:
                    data["language_config"] = get_language(settings.default_target_language)

        return await handler(event, data)
