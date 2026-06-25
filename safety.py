"""Wellness safety guardrails — crisis escalation and medical boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

CRISIS_RESPONSE = """\
I hear you, and I'm really glad you reached out. What you're describing is beyond what I can support as a fitness coach — but please know that you deserve real help from someone qualified.

**If you or someone you know is in immediate danger, please contact emergency services now.**

**Crisis support lines (free & confidential):**
- 🇺🇸 **US:** 988 Suicide & Crisis Lifeline — call or text **988**
- 🇬🇧 **UK & Ireland:** Samaritans — call **116 123**
- 🇪🇺 **EU:** Emergency — call **112**
- 🌍 **International:** [findahelpline.com](https://findahelpline.com)

Please reach out to one of these resources. A trained counselor can give you the support you need right now. You're not alone in this."""

MEDICAL_BOUNDARY_RESPONSE = """\
I really appreciate you trusting me with this — but this falls into medical territory, and I want to be honest about my limits.

I can't diagnose conditions, interpret symptoms, or give advice on medications or medical treatments. That kind of guidance needs to come from a doctor or licensed clinician who knows your full health picture.

**What I *can* help with:**
- General training programming and exercise selection
- Nutrition planning — macros, meal timing, calorie targets
- Workout modifications for common limitations
- General wellness and recovery strategies

If you've got a fitness or nutrition question, I'm right here for you."""

CRISIS_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(suicid|kill myself|end my life|want to die|self[- ]?harm)\b",
        r"\b(chest pain|heart attack|can'?t breathe|stroke|seizure)\b",
        r"\b(overdose|took too many pills)\b",
        r"\b(eating disorder|anorexi|bulimi|purging)\b.*\b(severe|hospital|dying)\b",
    )
]

MEDICAL_BLOCK_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(diagnos(e|is|ing)|what (disease|condition|illness) do i have)\b",
        r"\b(should i (take|stop)|prescrib(e|ed|ing)|dosage of)\b.*\b(medication|medicine|drug|antibiotic|insulin|steroid)\b",
        r"\b(interact(s|ion)? with)\b.*\b(medication|medicine|drug)\b",
        r"\b(am i (sick|ill)|do i have (cancer|diabetes|covid))\b",
        r"\b(symptom(s)?).{0,40}\b(cancer|tumor|blood pressure|diabetes)\b",
    )
]


class SafetyLevel(str, Enum):
    OK = "ok"
    CRISIS = "crisis"
    MEDICAL_BOUNDARY = "medical_boundary"


@dataclass(frozen=True)
class SafetyCheck:
    level: SafetyLevel
    response: str | None = None


def check_safety(user_message: str) -> SafetyCheck:
    """Run deterministic safety checks before any LLM call."""
    text = user_message.strip()
    if not text:
        return SafetyCheck(SafetyLevel.OK)

    for pattern in CRISIS_PATTERNS:
        if pattern.search(text):
            return SafetyCheck(SafetyLevel.CRISIS, CRISIS_RESPONSE)

    for pattern in MEDICAL_BLOCK_PATTERNS:
        if pattern.search(text):
            return SafetyCheck(SafetyLevel.MEDICAL_BOUNDARY, MEDICAL_BOUNDARY_RESPONSE)

    return SafetyCheck(SafetyLevel.OK)
