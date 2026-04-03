from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.config import settings
from src.db.models import User
from src.db.repository import (
    create_user,
    end_all_conversations,
    get_user,
    upsert_user,
)
from src.bot.handlers.callbacks import (
    NATIVE_LANGUAGES,
    PROFICIENCY_LEVELS,
    OnboardingStates,
)
from src.tutor.languages import LanguageConfig, get_supported_languages

router = Router()


def _build_language_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=lang.name, callback_data=f"target_lang:{lang.code}")]
        for lang in get_supported_languages()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_native_language_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"native_lang:{code}")]
        for code, name in NATIVE_LANGUAGES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_proficiency_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=level, callback_data=f"proficiency:{level}")]
        for level in PROFICIENCY_LEVELS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _ask_native_language(message: Message) -> None:
    await message.answer(
        "What's your native language?",
        reply_markup=_build_native_language_keyboard(),
    )


async def _ask_proficiency(message: Message) -> None:
    await message.answer(
        "What's your current proficiency level?",
        reply_markup=_build_proficiency_keyboard(),
    )


# ── /start ───────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    telegram_id = message.from_user.id
    user = await get_user(settings.database_path, telegram_id)

    if user is not None and user.display_name:
        await message.answer(
            f"Welcome back, {user.display_name}! Just send me a message to start practicing."
        )
        return

    await create_user(settings.database_path, telegram_id)
    await message.answer(
        "Welcome! I'm your language tutor bot. Let's get you set up.\n\n"
        "What should I call you? (Just type your name)"
    )
    await state.set_state(OnboardingStates.waiting_name)


@router.message(OnboardingStates.waiting_name)
async def on_name_received(message: Message, state: FSMContext) -> None:
    if not message.text or not message.from_user:
        return

    display_name = message.text.strip()
    await state.update_data(display_name=display_name)

    await message.answer(
        f"Nice to meet you, {display_name}! Which language do you want to learn?",
        reply_markup=_build_language_keyboard(),
    )
    await state.set_state(OnboardingStates.waiting_target_language)


# ── /language ────────────────────────────────────────────────────────

@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    await message.answer(
        "Which language would you like to learn?",
        reply_markup=_build_language_keyboard(),
    )


# ── /reset ───────────────────────────────────────────────────────────

@router.message(Command("reset"))
async def cmd_reset(
    message: Message, db_user: User | None = None, **kwargs: object
) -> None:
    if not message.from_user:
        return

    await end_all_conversations(settings.database_path, message.from_user.id)
    await message.answer("Conversation reset. Send a message to start a new one!")


# ── /level ───────────────────────────────────────────────────────────

@router.message(Command("level"))
async def cmd_level(message: Message) -> None:
    await message.answer(
        "Select your proficiency level:",
        reply_markup=_build_proficiency_keyboard(),
    )


# ── /help ────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "🤖 *Language Tutor Bot*\n\n"
        "Just send me a message in the language you're learning and I'll chat with you and correct your mistakes\\.\n\n"
        "*Commands:*\n"
        "/start — Set up your profile\n"
        "/language — Switch target language\n"
        "/level — Change proficiency level\n"
        "/reset — End current conversation\n"
        "/help — Show this message",
        parse_mode="MarkdownV2",
    )
