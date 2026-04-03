from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from src.config import settings
from src.db.repository import (
    end_all_conversations,
    upsert_user,
    update_user_language,
)
from src.tutor.languages import get_language, get_supported_languages

router = Router()


class OnboardingStates(StatesGroup):
    waiting_name = State()
    waiting_target_language = State()
    waiting_native_language = State()
    waiting_proficiency = State()


# ── Target language selection (onboarding + /language command) ────────

@router.callback_query(F.data.startswith("target_lang:"))
async def on_target_language_selected(
    callback: CallbackQuery, state: FSMContext
) -> None:
    if not callback.data or not callback.message:
        return
    lang_code = callback.data.split(":", 1)[1]

    try:
        lang_config = get_language(lang_code)
    except KeyError:
        await callback.answer("Language not supported.")
        return

    await callback.answer()
    state_data = await state.get_data()
    current_state = await state.get_state()

    # If this is from the /language command (not onboarding)
    if current_state is None and callback.from_user:
        await update_user_language(
            settings.database_path, callback.from_user.id, lang_code
        )
        await end_all_conversations(settings.database_path, callback.from_user.id)
        await callback.message.edit_text(
            f"Switched to {lang_config.name}! Previous conversation ended.\n\n{lang_config.greeting}"
        )
        return

    # Onboarding flow: save language, ask for native language
    await state.update_data(target_language=lang_code)

    from src.bot.handlers.commands import _ask_native_language
    await callback.message.edit_text(f"Great — {lang_config.name} it is!")
    await _ask_native_language(callback.message)
    await state.set_state(OnboardingStates.waiting_native_language)


# ── Native language selection ────────────────────────────────────────

NATIVE_LANGUAGES = {
    "ru": "Russian",
    "es": "Spanish",
    "zh": "Chinese",
    "other": "Other",
}


@router.callback_query(F.data.startswith("native_lang:"))
async def on_native_language_selected(
    callback: CallbackQuery, state: FSMContext
) -> None:
    if not callback.data or not callback.message:
        return
    lang_code = callback.data.split(":", 1)[1]
    lang_name = NATIVE_LANGUAGES.get(lang_code, lang_code)

    await callback.answer()
    await state.update_data(native_language=lang_code)
    await callback.message.edit_text(f"Native language: {lang_name}")

    from src.bot.handlers.commands import _ask_proficiency
    await _ask_proficiency(callback.message)
    await state.set_state(OnboardingStates.waiting_proficiency)


# ── Proficiency level selection ──────────────────────────────────────

PROFICIENCY_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


@router.callback_query(F.data.startswith("proficiency:"))
async def on_proficiency_selected(
    callback: CallbackQuery, state: FSMContext
) -> None:
    if not callback.data or not callback.from_user or not callback.message:
        return
    level = callback.data.split(":", 1)[1]

    await callback.answer()

    state_data = await state.get_data()
    current_state = await state.get_state()

    # If from /level command (not onboarding)
    if current_state is None or current_state == OnboardingStates.__name__:
        pass  # fall through to check

    # Check if this is a standalone /level change
    if "display_name" not in state_data and "target_language" not in state_data:
        await upsert_user(
            settings.database_path,
            callback.from_user.id,
            proficiency=level,
        )
        await callback.message.edit_text(f"Proficiency updated to {level}!")
        await state.clear()
        return

    # Onboarding: finalize user creation
    display_name = state_data.get("display_name", "Learner")
    target_language = state_data.get(
        "target_language", settings.default_target_language
    )
    native_language = state_data.get(
        "native_language", settings.default_native_language
    )

    user = await upsert_user(
        settings.database_path,
        callback.from_user.id,
        display_name=display_name,
        native_language=native_language,
        target_language=target_language,
        proficiency=level,
    )

    try:
        lang_config = get_language(target_language)
        greeting = lang_config.greeting
    except KeyError:
        greeting = "Let's start chatting!"

    await callback.message.edit_text(f"Proficiency: {level}")
    await callback.message.answer(
        f"You're all set, {display_name}! 🎉\n\n{greeting}"
    )
    await state.clear()
