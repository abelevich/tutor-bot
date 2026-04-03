from __future__ import annotations

import re

from aiogram import Bot
from aiogram.enums import ParseMode

from src.tutor.correction import TutorResponse

_MARKDOWNV2_SPECIAL = re.compile(r"([_*\[\]()~`>#+\-=|{}.!])")


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2, preserving **bold**."""
    # First, temporarily replace **bold** markers
    bold_pattern = re.compile(r"\*\*(.+?)\*\*")
    bold_segments: list[tuple[str, str]] = []

    def _save_bold(m: re.Match[str]) -> str:
        placeholder = f"\x00BOLD{len(bold_segments)}\x00"
        bold_segments.append((placeholder, m.group(1)))
        return placeholder

    text = bold_pattern.sub(_save_bold, text)

    # Escape all special chars
    text = _MARKDOWNV2_SPECIAL.sub(r"\\\1", text)

    # Restore bold markers (with escaped inner text already)
    for placeholder, inner in bold_segments:
        escaped_inner = inner  # already escaped by the global escape above
        text = text.replace(
            _MARKDOWNV2_SPECIAL.sub(r"\\\1", placeholder),
            f"*{escaped_inner}*",
        )

    return text


def format_reply(text: str) -> str:
    """Format the tutor's reply for sending as a plain text message."""
    return text.strip()


def format_correction(correction_text: str) -> str:
    """Format correction block with MarkdownV2 escaping."""
    return escape_markdown_v2(correction_text)


def split_message(text: str, max_length: int = 4096) -> list[str]:
    """Split text at sentence boundaries if too long."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current = ""

    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_length:
            if current:
                chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence

    if current:
        chunks.append(current.strip())

    return chunks if chunks else [text[:max_length]]


async def send_tutor_response(
    bot: Bot, chat_id: int, tutor_response: TutorResponse
) -> None:
    """Send reply + optional correction as separate messages."""
    # Send reply as plain text
    reply_parts = split_message(format_reply(tutor_response.reply))
    for part in reply_parts:
        await bot.send_message(chat_id, part)

    # Send correction if present
    if tutor_response.correction:
        correction_text = f"📝 *Corrections:*\n\n{format_correction(tutor_response.correction)}"
        correction_parts = split_message(correction_text)
        for part in correction_parts:
            try:
                await bot.send_message(
                    chat_id, part, parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception:
                # Fallback to plain text if MarkdownV2 parsing fails
                await bot.send_message(chat_id, tutor_response.correction)
                break
    else:
        # No corrections — append indicator to the last reply message
        await bot.send_message(chat_id, "✨ No corrections needed")
