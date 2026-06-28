"""
Exercise retriever for FitZone.
Provides search, filter, and format_for_llm methods over the exercise database.
Follows the same singleton pattern as nutrition_retriever.py.

Data source: https://github.com/yuhonas/free-exercise-db (public domain)
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from src.config import BASE_DIR

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

EXERCISES_JSON = BASE_DIR / "knowledge" / "exercises.json"


class ExerciseEntry:
    """A structured exercise entry."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.force: str = data.get("force", "") or ""
        self.level: str = data.get("level", "") or "intermediate"
        self.mechanic: str = data.get("mechanic", "") or ""
        equip = data.get("equipment", "")
        self.equipment: str = ", ".join(equip) if isinstance(equip, list) else (equip or "other")
        self.primary_muscles: list[str] = data.get("primaryMuscles") or data.get("target_muscles", [])
        self.secondary_muscles: list[str] = data.get("secondaryMuscles") or data.get("synergists", [])
        instructions = data.get("instructions", [])
        self.instructions: list[str] = instructions if isinstance(instructions, list) else [instructions]
        self.category: str = data.get("category", "") or "strength"
        self.fitzone_domain: str = data.get("fitzone_domain", "General Fitness")
        self.images: list[str] = data.get("images", [])
        self.all_muscles: list[str] = self.primary_muscles + self.secondary_muscles

    def to_text_block(self) -> str:
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


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


class ExerciseRetriever:
    """
    Singleton exercise retriever using TF-IDF over the exercise database.
    Provides search(), filter(), and format_for_llm() methods.
    """

    _instance: ExerciseRetriever | None = None

    def __new__(cls) -> ExerciseRetriever:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._entries: list[ExerciseEntry] = []
        self._idf: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []
        self._load()

    def _load(self) -> None:
        if not EXERCISES_JSON.exists():
            return
        data = json.loads(EXERCISES_JSON.read_text(encoding="utf-8"))
        self._entries = [ExerciseEntry(item) for item in data]
        self._build_tfidf()

    def _build_tfidf(self) -> None:
        """Build TF-IDF index over exercises."""
        if not self._entries:
            return
        doc_count = len(self._entries)
        df: Counter[str] = Counter()
        self._doc_tokens: list[list[str]] = []
        for entry in self._entries:
            name_tokens = _tokenize(entry.name)
            cat_tokens = _tokenize(entry.category)
            muscle_tokens = _tokenize(" ".join(entry.all_muscles))
            equip_tokens = _tokenize(entry.equipment)
            tokens = name_tokens + cat_tokens + muscle_tokens + equip_tokens
            self._doc_tokens.append(tokens)
            for token in set(tokens):
                df[token] += 1
        self._idf = {
            token: math.log((1 + doc_count) / (1 + freq)) + 1.0
            for token, freq in df.items()
        }
        self._vectors = [self._tfidf_vector(tokens) for tokens in self._doc_tokens]

    def _tfidf_vector(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        total = sum(counts.values()) or 1
        return {
            token: (count / total) * self._idf.get(token, 1.0)
            for token, count in counts.items()
        }

    @staticmethod
    def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        common = set(vec_a) & set(vec_b)
        dot = sum(vec_a[t] * vec_b[t] for t in common)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: str, top_k: int = 5) -> list[ExerciseEntry]:
        """
        TF-IDF search over exercise entries.
        Searches by name, category, muscles, and equipment.
        """
        if not self._entries or not self._vectors:
            return []
        query_tokens = _tokenize(query)
        query_vec = self._tfidf_vector(query_tokens)
        scored: list[tuple[float, int]] = []
        for idx, vec in enumerate(self._vectors):
            score = self._cosine_similarity(query_vec, vec)
            if score > 0:
                scored.append((score, idx))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._entries[idx] for _, idx in scored[:top_k]]

    def filter(
        self,
        category: str | None = None,
        level: str | None = None,
        equipment: str | None = None,
        mechanic: str | None = None,
        primary_muscle: str | None = None,
        force: str | None = None,
    ) -> list[ExerciseEntry]:
        """
        Structured filter over exercise entries.
        All filters are AND-combined.
        """
        results: list[ExerciseEntry] = []
        for entry in self._entries:
            if category and entry.category.lower() != category.lower():
                continue
            if level and entry.level.lower() != level.lower():
                continue
            if equipment and entry.equipment.lower() != equipment.lower():
                continue
            if mechanic and entry.mechanic.lower() != mechanic.lower():
                continue
            if force and entry.force.lower() != force.lower():
                continue
            if primary_muscle:
                pm_lower = [m.lower() for m in entry.primary_muscles]
                sm_lower = [m.lower() for m in entry.secondary_muscles]
                all_lower = pm_lower + sm_lower
                if not any(primary_muscle.lower() in m for m in all_lower):
                    continue
            results.append(entry)
        return results

    def get_by_id(self, exercise_id: str) -> ExerciseEntry | None:
        """Look up an exercise by ID."""
        for entry in self._entries:
            if entry.id == exercise_id:
                return entry
        return None

    def get_by_name(self, name: str) -> ExerciseEntry | None:
        """Look up an exercise by exact or partial name match."""
        name_lower = name.lower()
        for entry in self._entries:
            if name_lower == entry.name.lower():
                return entry
        for entry in self._entries:
            if name_lower in entry.name.lower():
                return entry
        return None

    def list_categories(self) -> list[str]:
        """Return all unique categories."""
        return sorted(set(e.category for e in self._entries if e.category))

    def list_equipment(self) -> list[str]:
        """Return all unique equipment types."""
        return sorted(set(e.equipment for e in self._entries if e.equipment))

    def list_levels(self) -> list[str]:
        """Return all unique difficulty levels."""
        return sorted(set(e.level for e in self._entries if e.level))

    def list_muscles(self) -> list[str]:
        """Return all unique muscles targeted."""
        muscles: set[str] = set()
        for entry in self._entries:
            for m in entry.all_muscles:
                muscles.add(m.lower())
        return sorted(muscles)

    def format_for_llm(self, entries: list[ExerciseEntry]) -> str:
        """
        Format exercise entries into a clean, prompt-injectable context string.
        """
        if not entries:
            return ""
        lines = ["[EXERCISE KNOWLEDGE BASE]"]
        for entry in entries:
            muscle_str = ", ".join(entry.primary_muscles)
            if entry.secondary_muscles:
                muscle_str += f" + {', '.join(entry.secondary_muscles)}"
            lines.append(
                f"- **{entry.name}** ({entry.category}, {entry.level}) ? "
                f"Equipment: {entry.equipment} | "
                f"Muscles: {muscle_str} | "
                f"Force: {entry.force or 'N/A'}"
            )
        return "\n".join(lines)

    @property
    def count(self) -> int:
        return len(self._entries)


def get_exercise_retriever() -> ExerciseRetriever:
    """Get the singleton ExerciseRetriever instance."""
    return ExerciseRetriever()
