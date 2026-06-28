"""
Persistent user profile manager for FitZone.
Stores physical metrics, goals, preferences, and constraints per user.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import CACHE_DIR

PROFILES_DIR = CACHE_DIR / "profiles"

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

_WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:kg|kgs|lbs?|pounds?)", re.IGNORECASE)
_HEIGHT_CM_RE = re.compile(r"(\d{2,3})\s*(?:cm|centimeter)", re.IGNORECASE)
_HEIGHT_FT_RE = re.compile(r"(\d)'\s*(\d{1,2})", re.IGNORECASE)
_AGE_RE = re.compile(r"(\d{1,2})\s*(?:years?\s*old|yr|yo)", re.IGNORECASE)
_GENDER_RE = re.compile(r"\b(male|female|man|woman|guy|girl|boy)\b", re.IGNORECASE)
_BODYFAT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:body\s*fat|bf|bodyfat)", re.IGNORECASE)
_GOAL_RE = re.compile(
    r"\b(bulking?|cutting?|lean\s*bulk|recomp|maintain|lose\s*weight|"
    r"build\s*muscle|gain\s*muscle|shred|get\s*stronger|hypertrophy|strength)\b",
    re.IGNORECASE,
)
_EXPERIENCE_RE = re.compile(
    r"\b(beginner|novice|intermediate|advanced|new\s*to\s*(?:lifting|training|gym))\b",
    re.IGNORECASE,
)
_SLEEP_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:hours?\s*(?:of\s*)?sleep|hrs?\s*sleep)", re.IGNORECASE)
_FREQ_RE = re.compile(
    r"(\d+)\s*(?:days?\s*(?:a|per)\s*(?:week|wk)|x\s*(?:a|per)\s*(?:week|wk))",
    re.IGNORECASE,
)
_EQUIPMENT_RE = re.compile(
    r"\b(home\s*gym|garage\s*gym|dumbbells?\s*only|bodyweight\s*only|"
    r"commercial\s*gym|barbell|kettlebell|resistance\s*bands|cable|machine)\b",
    re.IGNORECASE,
)
_INJURY_RE = re.compile(
    r"\b(injured?\s*(?:my|the|left|right)?\s*(knee|shoulder|back|hip|elbow|"
    r"wrist|ankle|neck|hamstring|quad|groin|rotator\s*cuff))\b",
    re.IGNORECASE,
)


@dataclass
class UserProfile:
    user_id: str
    name: str | None = None
    weight_kg: float | None = None
    height_cm: float | None = None
    age: int | None = None
    gender: str | None = None
    body_fat_pct: float | None = None
    primary_goal: str | None = None
    secondary_goal: str | None = None
    experience_level: str | None = None
    training_frequency: int | None = None
    sleep_hours: float | None = None
    stress_level: int | None = None
    diet_type: str | None = None
    preferred_personality: str = "coach"
    science_mode: bool = False
    injuries: list[str] = field(default_factory=list)
    medical_conditions: list[str] = field(default_factory=list)
    equipment_available: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        return cls(**{k: data.get(k) for k in cls.__dataclass_fields__})

    def format_for_context(self) -> str:
        lines = []
        if self.weight_kg:
            lines.append(f"  Weight: {self.weight_kg} kg")
        if self.height_cm:
            lines.append(f"  Height: {self.height_cm} cm")
        if self.age:
            lines.append(f"  Age: {self.age}")
        if self.gender:
            lines.append(f"  Gender: {self.gender}")
        if self.body_fat_pct is not None:
            lines.append(f"  Body fat: {self.body_fat_pct}%")
        if self.primary_goal:
            lines.append(f"  Goal: {self.primary_goal.replace('_', ' ').title()}"
                         + (f" (secondary: {self.secondary_goal.replace('_', ' ').title()})" if self.secondary_goal else ""))
        if self.experience_level:
            lines.append(f"  Experience: {self.experience_level.title()}")
        if self.training_frequency:
            lines.append(f"  Training frequency: {self.training_frequency}x/week")
        if self.sleep_hours:
            lines.append(f"  Sleep: {self.sleep_hours} hrs/night")
        if self.stress_level:
            lines.append(f"  Stress: {self.stress_level}/10")
        if self.diet_type:
            lines.append(f"  Diet preference: {self.diet_type}")
        if self.injuries:
            lines.append(f"  Injuries/recovery areas: {', '.join(self.injuries)}")
        if self.equipment_available:
            lines.append(f"  Equipment: {', '.join(self.equipment_available)}")
        if not lines:
            return ""
        return "## User Profile\n" + "\n".join(lines)


def extract_profile_from_text(text: str) -> dict[str, Any]:
    """Extract profile fields from natural language text."""
    updates: dict[str, Any] = {}

    m = _WEIGHT_RE.search(text)
    if m:
        val = float(m.group(1))
        unit = "kg" if "kg" in m.group(0).lower() else "lbs"
        if unit == "kg":
            updates["weight_kg"] = val
        else:
            updates["weight_kg"] = round(val * 0.453592, 1)

    m = _HEIGHT_CM_RE.search(text)
    if m:
        updates["height_cm"] = int(m.group(1))

    m = _HEIGHT_FT_RE.search(text)
    if m:
        feet, inches = int(m.group(1)), int(m.group(2))
        updates["height_cm"] = round(feet * 30.48 + inches * 2.54)

    m = _AGE_RE.search(text)
    if m:
        updates["age"] = int(m.group(1))

    m = _GENDER_RE.search(text)
    if m:
        g = m.group(1).lower()
        if g in ("male", "man", "guy", "boy"):
            updates["gender"] = "male"
        elif g in ("female", "woman", "girl"):
            updates["gender"] = "female"

    m = _BODYFAT_RE.search(text)
    if m:
        updates["body_fat_pct"] = float(m.group(1))

    m = _GOAL_RE.search(text)
    if m:
        updates["primary_goal"] = m.group(1).lower()

    m = _EXPERIENCE_RE.search(text)
    if m:
        raw = m.group(1).lower()
        if raw in ("new to lifting", "new to training", "new to gym"):
            updates["experience_level"] = "beginner"
        else:
            updates["experience_level"] = raw

    m = _SLEEP_RE.search(text)
    if m:
        updates["sleep_hours"] = float(m.group(1))

    m = _FREQ_RE.search(text)
    if m:
        updates["training_frequency"] = int(m.group(1))

    m = _INJURY_RE.search(text)
    if m:
        injury = m.group(2).lower()
        if injury not in updates.get("injuries", []):
            updates.setdefault("injuries", []).append(injury)

    m = _EQUIPMENT_RE.search(text)
    if m:
        equip = m.group(1).lower()
        if equip not in updates.get("equipment_available", []):
            updates.setdefault("equipment_available", []).append(equip)

    return updates


def merge_profile(current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Merge extracted updates into existing profile, preferring new values."""
    merged = dict(current)
    for key, val in updates.items():
        if val is not None and val != []:
            if key in ("injuries", "equipment_available", "medical_conditions"):
                existing = set(merged.get(key, []))
                if isinstance(val, list):
                    existing.update(val)
                else:
                    existing.add(val)
                merged[key] = sorted(existing)
            else:
                merged[key] = val
    return merged


class ProfileStore:
    """Persistent user profile storage (JSON-backed, atomic writes)."""

    def __init__(self, profiles_dir: Path = PROFILES_DIR) -> None:
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def _profile_path(self, user_id: str) -> Path:
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return self.profiles_dir / f"{safe_id}.json"

    def load(self, user_id: str) -> UserProfile:
        path = self._profile_path(user_id)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return UserProfile.from_dict(data)
            except (json.JSONDecodeError, OSError):
                pass
        return UserProfile(user_id=user_id, created_at=datetime.now(timezone.utc).isoformat())

    def save(self, profile: UserProfile) -> None:
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        if not profile.created_at:
            profile.created_at = profile.updated_at
        data = profile.to_dict()
        path = self._profile_path(profile.user_id)
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        fd, tmp_path = tempfile.mkstemp(dir=self.profiles_dir, suffix=".tmp")
        try:
            os.write(fd, payload)
        finally:
            os.close(fd)
        os.replace(tmp_path, path)

    def update_from_conversation(self, user_id: str, text: str) -> UserProfile:
        profile = self.load(user_id)
        updates = extract_profile_from_text(text)
        merged = merge_profile(profile.to_dict(), updates)
        updated = UserProfile.from_dict(merged)
        self.save(updated)
        return updated
