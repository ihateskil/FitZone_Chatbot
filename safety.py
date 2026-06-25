"""Wellness safety guardrails — crisis escalation and medical boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

CRISIS_RESPONSE = """I'm really glad you reached out, but this is beyond what I can help with as a fitness coach.

**If you or someone else may be in immediate danger, call emergency services now** (e.g. 911 in the US, 999 in the UK, 112 in the EU).

**Mental health support:**
- US: 988 Suicide & Crisis Lifeline (call or text 988)
- UK & ROI: Samaritans at 116 123
- International: findahelpline.com

Please speak with a licensed healthcare professional or crisis counselor right away. You deserve real support from someone qualified to help."""

MEDICAL_BOUNDARY_RESPONSE = """I can share general fitness and nutrition education, but I can't diagnose conditions, interpret symptoms, or advise on medications or medical treatment.

For anything involving symptoms, injuries, chronic conditions, pregnancy, or prescriptions, please check with a doctor or licensed clinician who knows your full health picture.

I'm happy to help with training, macros, workouts, or general wellness questions within that scope."""

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
