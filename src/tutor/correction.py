from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ErrorDetail:
    original: str
    corrected: str
    explanation: str
    severity: str  # "red", "yellow", "green"


@dataclass
class TutorResponse:
    reply: str
    correction: str | None
    raw: str


def parse_tutor_response(text: str) -> TutorResponse:
    """Extract <reply> and <correction> blocks from the tutor response.

    Falls back to treating the entire text as the reply if tags are missing.
    """
    reply_match = re.search(r"<reply>(.*?)</reply>", text, re.DOTALL)
    correction_match = re.search(
        r"<correction>(.*?)</correction>", text, re.DOTALL
    )

    reply = reply_match.group(1).strip() if reply_match else text.strip()

    correction: str | None = None
    if correction_match:
        raw_correction = correction_match.group(1).strip()
        if raw_correction and "no corrections needed" not in raw_correction.lower():
            correction = raw_correction

    return TutorResponse(reply=reply, correction=correction, raw=text)


_SEVERITY_MAP = {
    "🔴": "red",
    "🟡": "yellow",
    "🟢": "green",
}


def parse_error_details(correction_text: str) -> list[ErrorDetail]:
    """Extract individual error entries from a correction block.

    Parses the structured format:
      - Original: ...
      - Corrected: ...
      - Fixes:
        - 🔴/🟡/🟢 explanation
    """
    errors: list[ErrorDetail] = []

    original_match = re.search(
        r"-\s*Original:\s*(.+?)(?:\n|$)", correction_text
    )
    corrected_match = re.search(
        r"-\s*Corrected:\s*(.+?)(?:\n|$)", correction_text
    )

    original = original_match.group(1).strip() if original_match else ""
    corrected = corrected_match.group(1).strip() if corrected_match else ""

    fix_pattern = re.compile(r"-\s*(🔴|🟡|🟢)\s*(.+?)(?=\n\s*-\s*[🔴🟡🟢]|\Z)", re.DOTALL)
    for match in fix_pattern.finditer(correction_text):
        emoji = match.group(1)
        explanation = match.group(2).strip()
        severity = _SEVERITY_MAP.get(emoji, "yellow")
        errors.append(
            ErrorDetail(
                original=original,
                corrected=corrected,
                explanation=explanation,
                severity=severity,
            )
        )

    return errors
