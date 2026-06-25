"""Input validation and basic prompt-injection filtering."""

from __future__ import annotations

import re
from dataclasses import dataclass

from config import MAX_MESSAGE_LENGTH

INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore (all )?(previous|prior|above) instructions",
        r"disregard (your|the) (system )?prompt",
        r"you are now (a |an )?",
        r"act as (if you|a) (have )?no restrictions",
        r"jailbreak",
        r"reveal (your|the) (system )?prompt",
        r"<\s*/?\s*system\s*>",
    )
]


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    message: str = ""
    cleaned: str = ""


def validate_user_input(text: str) -> ValidationResult:
    """Validate and lightly sanitize user input."""
    cleaned = " ".join(text.split()).strip()

    if not cleaned:
        return ValidationResult(False, "Please enter a message.")

    if len(cleaned) > MAX_MESSAGE_LENGTH:
        return ValidationResult(
            False,
            f"Message is too long ({len(cleaned)} chars). "
            f"Please keep it under {MAX_MESSAGE_LENGTH} characters.",
        )

    for pattern in INJECTION_PATTERNS:
        if pattern.search(cleaned):
            return ValidationResult(
                False,
                "That message can't be processed. Please ask a fitness or nutrition question.",
            )

    return ValidationResult(True, cleaned=cleaned)
