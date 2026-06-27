"""
Exercise database ingestion script for FitZone.
Downloads exercises from the free-exercise-db GitHub repo (public domain)
and produces knowledge/exercises.json and knowledge/exercises.txt.

Source: https://github.com/yuhonas/free-exercise-db
License: Public Domain / MIT
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

KNOWLEDGE_DIR = BASE_DIR / "knowledge"
EXERCISES_JSON = KNOWLEDGE_DIR / "exercises.json"
EXERCISES_TXT = KNOWLEDGE_DIR / "exercises.txt"

USER_AGENT = "FitZone-Chatbot/1.0 (fitness-nutrition-assistant)"
EXERCISES_DB_URL = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"



# Fitzone domain mapping for categorization
CATEGORY_DOMAIN_MAP = {
    "strength": "Strength & Hypertrophy Training",
    "powerlifting": "Strength & Hypertrophy Training",
    "olympic weightlifting": "Sport-Specific Training",
    "strongman": "Sport-Specific Training",
    "plyometrics": "Strength & Hypertrophy Training",
    "stretching": "Mobility & Flexibility",
    "cardio": "Cardiovascular & Endurance Training",
}


class ExerciseEntry:
    """A normalized exercise entry."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.id: str = raw.get("id", "")
        self.name: str = raw.get("name", "")
        self.force: str = raw.get("force", "") or ""
        self.level: str = raw.get("level", "") or "intermediate"
        self.mechanic: str = raw.get("mechanic", "") or ""
        self.equipment: str = raw.get("equipment", "") or "other"
        self.primary_muscles: list[str] = raw.get("primaryMuscles", [])
        self.secondary_muscles: list[str] = raw.get("secondaryMuscles", [])
        self.instructions: list[str] = raw.get("instructions", [])
        self.category: str = raw.get("category", "") or "strength"
        self.images: list[str] = raw.get("images", [])
        self.fitzone_domain: str = CATEGORY_DOMAIN_MAP.get(self.category, "General Fitness")
        self.all_muscles: list[str] = self.primary_muscles + self.secondary_muscles

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "force": self.force,
            "level": self.level,
            "mechanic": self.mechanic,
            "equipment": self.equipment,
            "primaryMuscles": self.primary_muscles,
            "secondaryMuscles": self.secondary_muscles,
            "instructions": self.instructions,
            "category": self.category,
            "fitzone_domain": self.fitzone_domain,
            "images": self.images,
            "all_muscles": self.all_muscles,
        }

    def to_text_block(self) -> str:
        """Format as a text block for TF-IDF retrieval."""
        parts = [f"Exercise: {self.name}"]
        parts.append(f"Category: {self.category}")
        parts.append(f"Domain: {self.fitzone_domain}")
        if self.level:
            parts.append(f"Level: {self.level}")
        if self.mechanic:
            parts.append(f"Mechanic: {self.mechanic}")
        if self.equipment:
            parts.append(f"Equipment: {self.equipment}")
        if self.force:
            parts.append(f"Force: {self.force}")
        if self.primary_muscles:
            parts.append(f"Primary muscles: {', '.join(self.primary_muscles)}")
        if self.secondary_muscles:
            parts.append(f"Secondary muscles: {', '.join(self.secondary_muscles)}")
        if self.instructions:
            parts.append(f"Instructions: {' '.join(self.instructions)}")
        return " | ".join(parts)


def download_exercises() -> list[dict[str, Any]]:
    """Download exercises from the free-exercise-db GitHub repo."""
    print("Downloading free-exercise-db from GitHub...")
    try:
        request = urllib.request.Request(EXERCISES_DB_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        print(f"  Downloaded {len(data)} exercises")
        return data
    except Exception as exc:
        print(f"  Download failed: {exc}")
        return []


def ingest_exercises() -> tuple[int, dict[str, int]]:
    """
    Download exercises, normalize, write JSON + TXT.
    Returns (total_count, category_breakdown).
    """
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    raw_data = download_exercises()
    if not raw_data:
        print("ERROR: No exercise data available")
        return 0, {}

    # Normalize
    entries = [ExerciseEntry(raw) for raw in raw_data]

    # Write JSON
    json_data = [e.to_dict() for e in entries]
    EXERCISES_JSON.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write TXT (for TF-IDF retrieval)
    text_blocks = [e.to_text_block() for e in entries]
    EXERCISES_TXT.write_text("\n\n----\n\n".join(text_blocks), encoding="utf-8")

    # Compute stats
    categories: dict[str, int] = {}
    levels: dict[str, int] = {}
    equipment: dict[str, int] = {}
    for entry in entries:
        categories[entry.category] = categories.get(entry.category, 0) + 1
        levels[entry.level] = levels.get(entry.level, 0) + 1
        equipment[entry.equipment] = equipment.get(entry.equipment, 0) + 1

    # Print summary
    print()
    print("=" * 60)
    print("EXERCISE DATABASE INGESTION COMPLETE")
    print("=" * 60)
    print(f"Total exercises: {len(entries)}")
    print(f"\nCategory breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print(f"\nLevel breakdown:")
    for lvl, count in sorted(levels.items(), key=lambda x: -x[1]):
        print(f"  {lvl}: {count}")
    print(f"\nTop equipment types:")
    for eq, count in sorted(equipment.items(), key=lambda x: -x[1])[:10]:
        print(f"  {eq}: {count}")
    print(f"\nFiles written:")
    print(f"  {EXERCISES_JSON}")
    print(f"  {EXERCISES_TXT}")
    print("=" * 60)

    return len(entries), categories


if __name__ == "__main__":
    count, breakdown = ingest_exercises()
    print(f"\nDone. {count} exercises available.")
