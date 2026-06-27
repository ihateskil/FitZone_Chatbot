"""
Nutrition retriever for FitZone.
Provides search, filter, and format_for_llm methods over nutrition data.
Follows the same singleton pattern as exercise_retriever.py.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.config import BASE_DIR

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

NUTRITION_JSON = BASE_DIR / "knowledge" / "nutrition.json"


class NutritionEntry:
    """A structured nutrition entry."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.name: str = data.get("name", "")
        self.source: str = data.get("source", "")
        self.category: str = data.get("category", "")
        self.serving_size: str = data.get("serving_size", "100g")
        self.kcal_100g: float | None = data.get("kcal_100g")
        self.protein_100g: float | None = data.get("protein_100g")
        self.carbs_100g: float | None = data.get("carbs_100g")
        self.fat_100g: float | None = data.get("fat_100g")
        self.fiber_100g: float | None = data.get("fiber_100g")
        self.sugar_100g: float | None = data.get("sugar_100g")
        self.sodium_mg_100g: float | None = data.get("sodium_mg_100g")

    @property
    def protein_per_100cal(self) -> float | None:
        """Protein per 100 calories ? useful for high-protein filtering."""
        if self.protein_100g is not None and self.kcal_100g and self.kcal_100g > 0:
            return round(self.protein_100g / self.kcal_100g * 100, 1)
        return None

    @property
    def is_high_protein(self) -> bool:
        """High protein = at least 8g protein per 100 calories."""
        pp100 = self.protein_per_100cal
        return pp100 is not None and pp100 >= 8.0

    @property
    def is_low_carb(self) -> bool:
        """Low carb = less than 10g net carbs per 100g."""
        if self.carbs_100g is not None:
            fiber = self.fiber_100g or 0
            return (self.carbs_100g - fiber) < 10
        return False

    @property
    def is_low_fat(self) -> bool:
        """Low fat = less than 3g fat per 100g."""
        return self.fat_100g is not None and self.fat_100g < 3.0

    def to_text_block(self) -> str:
        parts = [f"Food: {self.name}"]
        parts.append(f"Source: {self.source}")
        if self.category:
            parts.append(f"Category: {self.category}")
        parts.append(f"Serving: {self.serving_size}")
        macros = []
        if self.kcal_100g is not None:
            macros.append(f"{self.kcal_100g} kcal")
        if self.protein_100g is not None:
            macros.append(f"{self.protein_100g}g protein")
        if self.carbs_100g is not None:
            macros.append(f"{self.carbs_100g}g carbs")
        if self.fat_100g is not None:
            macros.append(f"{self.fat_100g}g fat")
        if self.fiber_100g is not None:
            macros.append(f"{self.fiber_100g}g fiber")
        if self.sugar_100g is not None:
            macros.append(f"{self.sugar_100g}g sugar")
        if macros:
            parts.append(f"Per 100g: {', '.join(macros)}")
        return " | ".join(parts)


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


class NutritionRetriever:
    """
    Singleton nutrition retriever using TF-IDF over the nutrition database.
    Provides search(), filter(), and format_for_llm() methods.
    """

    _instance: NutritionRetriever | None = None

    def __new__(cls) -> NutritionRetriever:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._entries: list[NutritionEntry] = []
        self._idf: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []
        self._load()

    def _load(self) -> None:
        if not NUTRITION_JSON.exists():
            return
        data = json.loads(NUTRITION_JSON.read_text(encoding="utf-8"))
        self._entries = [NutritionEntry(item) for item in data]
        self._build_tfidf()

    def _build_tfidf(self) -> None:
        """Build TF-IDF index over nutrition entries."""
        if not self._entries:
            return
        doc_count = len(self._entries)
        df: Counter[str] = Counter()
        self._doc_tokens: list[list[str]] = []
        for entry in self._entries:
            name_tokens = _tokenize(entry.name)
            cat_tokens = _tokenize(entry.category)
            tokens = name_tokens + cat_tokens
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

    def search(self, query: str, top_k: int = 5) -> list[NutritionEntry]:
        """
        TF-IDF search over nutrition entries.
        Returns top-k matching entries.
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
        high_protein: bool = False,
        low_carb: bool = False,
        low_fat: bool = None,
        min_protein: float | None = None,
        max_calories: float | None = None,
    ) -> list[NutritionEntry]:
        """
        Structured filter over nutrition entries.
        All filters are AND-combined.
        """
        results: list[NutritionEntry] = []
        for entry in self._entries:
            if category and entry.category.lower() != category.lower():
                continue
            if high_protein and not entry.is_high_protein:
                continue
            if low_carb and not entry.is_low_carb:
                continue
            if low_fat is True and not entry.is_low_fat:
                continue
            if low_fat is False and entry.is_low_fat:
                continue
            if min_protein is not None:
                if entry.protein_100g is None or entry.protein_100g < min_protein:
                    continue
            if max_calories is not None:
                if entry.kcal_100g is None or entry.kcal_100g > max_calories:
                    continue
            results.append(entry)
        return results

    def get_by_name(self, name: str) -> NutritionEntry | None:
        """Look up a food by exact or partial name match."""
        name_lower = name.lower()
        for entry in self._entries:
            if name_lower == entry.name.lower():
                return entry
        # Partial match fallback
        for entry in self._entries:
            if name_lower in entry.name.lower():
                return entry
        return None

    def list_categories(self) -> list[str]:
        """Return all unique categories."""
        return sorted(set(e.category for e in self._entries if e.category))

    def format_for_llm(self, entries: list[NutritionEntry]) -> str:
        """
        Format nutrition entries into a clean, prompt-injectable context string.
        """
        if not entries:
            return ""
        lines = ["[NUTRITION KNOWLEDGE BASE]"]
        for entry in entries:
            macros = []
            if entry.kcal_100g is not None:
                macros.append(f"{entry.kcal_100g} kcal")
            if entry.protein_100g is not None:
                macros.append(f"{entry.protein_100g}g protein")
            if entry.carbs_100g is not None:
                macros.append(f"{entry.carbs_100g}g carbs")
            if entry.fat_100g is not None:
                macros.append(f"{entry.fat_100g}g fat")
            macro_str = ", ".join(macros)
            suffix = f" (high protein)" if entry.is_high_protein else ""
            suffix += f" (low carb)" if entry.is_low_carb else ""
            lines.append(f"- **{entry.name}**{suffix} ? {macro_str} per {entry.serving_size}")
        return "\n".join(lines)

    @property
    def count(self) -> int:
        return len(self._entries)


def get_nutrition_retriever() -> NutritionRetriever:
    """Get the singleton NutritionRetriever instance."""
    return NutritionRetriever()
