from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LanguageConfig:
    code: str  # "en", "es", "de"
    name: str  # "English", "Spanish", "German"
    native_hints: dict[str, str]  # native_lang_code → common mistake patterns
    example_corrections: str  # few-shot examples for the system prompt
    greeting: str  # initial tutor greeting in target language


LANGUAGES: dict[str, LanguageConfig] = {
    "en": LanguageConfig(
        code="en",
        name="English",
        native_hints={
            "ru": (
                "Common issues for Russian speakers: articles (a/the) since Russian has none, "
                "preposition choices (in/on/at), verb tense consistency, word order in questions, "
                "forgetting subject pronouns, confusing 'make' and 'do', "
                "literal translations of Russian idioms"
            ),
            "es": (
                "Common issues for Spanish speakers: subject pronouns (English requires them), "
                "false cognates, adjective placement (before noun in English), "
                "third-person singular -s, use of present perfect vs simple past"
            ),
            "zh": (
                "Common issues for Chinese speakers: articles (a/the), plural forms, "
                "verb tenses (Chinese has no conjugation), prepositions, "
                "subject-verb agreement, countable vs uncountable nouns"
            ),
        },
        example_corrections=(
            "Example 1:\n"
            "User: I go to shop yesterday and buy new phone.\n"
            "Correction:\n"
            "- Original: I go to shop yesterday and buy new phone.\n"
            "- Corrected: I **went** to **the** shop yesterday and **bought** a new phone.\n"
            "- Fixes:\n"
            '  - 🔴 "go" → "went", "buy" → "bought": Past tense required because of "yesterday"\n'
            '  - 🟡 "to shop" → "to the shop": English requires an article before singular countable nouns\n'
            '  - 🟢 "new phone" → "a new phone": Use "a" when mentioning something for the first time\n'
            "\n"
            "Example 2:\n"
            "User: Can you explain me how works this?\n"
            "Correction:\n"
            "- Original: Can you explain me how works this?\n"
            "- Corrected: Can you explain **to** me how **this works**?\n"
            "- Fixes:\n"
            '  - 🟡 "explain me" → "explain to me": "explain" requires the preposition "to" before the indirect object\n'
            '  - 🟡 "how works this" → "how this works": In embedded questions, use statement word order (subject before verb)\n'
        ),
        greeting=(
            "Hi! I'm your English tutor. Let's chat — just talk to me naturally "
            "and I'll help you improve. What's on your mind?"
        ),
    ),
}


def get_language(code: str) -> LanguageConfig:
    """Get a language config by code. Raises KeyError if not found."""
    return LANGUAGES[code]


def get_supported_languages() -> list[LanguageConfig]:
    """Return all supported language configs."""
    return list(LANGUAGES.values())


def get_native_hints(target_lang: str, native_lang: str) -> str | None:
    """Get native-speaker-specific hints for a target language, or None."""
    lang = LANGUAGES.get(target_lang)
    if lang is None:
        return None
    return lang.native_hints.get(native_lang)
