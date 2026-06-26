"""
Open Food Facts API client for live food and nutrition lookups.
https://world.openfoodfacts.org
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from src.config import API_TIMEOUT_SEC, LLM_RETRY_ATTEMPTS
from src.retry_utils import with_retries

SEARCH_URL = "https://search.openfoodfacts.org/search"
LEGACY_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
USER_AGENT = "FitZone-Chatbot/1.0 (fitness-nutrition-assistant)"

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

FOOD_QUERY_SIGNALS = frozenset(
    {
        "calorie", "calories", "kcal", "macro", "macros", "protein", "carb", "carbs",
        "fat", "fats", "nutrition", "nutrients", "food", "foods", "eat", "eating",
        "meal", "meals", "snack", "snacks", "breakfast", "lunch", "dinner",
        "ingredient", "serving", "gram", "grams", "oz", "ounce", "diet", "intake",
        "apple", "banana", "chicken", "rice", "salmon", "yogurt", "egg", "eggs",
        "oatmeal", "pasta", "bread", "milk", "cheese", "beef", "pork", "fish",
        "vegetable", "fruit", "smoothie", "shake", "supplement", "whey",
        # Additional common foods
        "tuna", "turkey", "steak", "avocado", "potato", "sweet", "broccoli",
        "spinach", "almond", "peanut", "butter", "greek", "cottage", "tofu",
        "quinoa", "lentil", "lentils", "beans", "chickpea", "chickpeas",
    }
)

FOOD_SEARCH_STOPWORDS = frozenset(
    {
        "how", "many", "much", "what", "is", "are", "the", "in", "a", "an", "of",
        "for", "per", "does", "do", "have", "has", "there", "about", "tell", "me",
        "give", "show", "find", "get", "can", "you", "i", "my", "need", "want",
        "calorie", "calories", "kcal", "macro", "macros", "protein", "carb",
        "carbs", "fat", "nutrition", "nutrients", "gram", "grams", "serving",
    }
)


@dataclass
class FoodProduct:
    name: str
    brand: str
    serving_size: str
    kcal_100g: float | None
    protein_100g: float | None
    carbs_100g: float | None
    fat_100g: float | None
    barcode: str

    def to_context_line(self) -> str:
        def fmt(value: float | None, unit: str) -> str:
            return f"{value}{unit}" if value is not None else "—"

        brand_part = f" by {self.brand}" if self.brand else ""
        return (
            f"• {self.name}{brand_part} "
            f"(serving: {self.serving_size or '100g'}) — "
            f"{fmt(self.kcal_100g, ' kcal')}, "
            f"{fmt(self.protein_100g, 'g protein')}, "
            f"{fmt(self.carbs_100g, 'g carbs')}, "
            f"{fmt(self.fat_100g, 'g fat')} per 100g"
        )


class OpenFoodFactsClient:
    """Search Open Food Facts and format nutrition data for RAG context."""

    def __init__(self, page_size: int = 5, timeout: float = API_TIMEOUT_SEC) -> None:
        self.page_size = page_size
        self.timeout = timeout

    @staticmethod
    def is_food_query(query: str) -> bool:
        tokens = set(TOKEN_PATTERN.findall(query.lower()))
        return bool(tokens & FOOD_QUERY_SIGNALS)

    @staticmethod
    def extract_search_terms(query: str) -> str:
        tokens = [
            token
            for token in TOKEN_PATTERN.findall(query.lower())
            if token not in FOOD_SEARCH_STOPWORDS and len(token) > 1
        ]
        if not tokens:
            return query.strip()
        return " ".join(tokens[:8])

    def search(self, search_terms: str) -> list[FoodProduct]:
        products = self._search_searchalicious(search_terms)
        if products:
            return products
        return self._search_legacy(search_terms)

    def _search_searchalicious(self, search_terms: str) -> list[FoodProduct]:
        params = urllib.parse.urlencode(
            {
                "q": search_terms,
                "page": 1,
                "page_size": self.page_size,
            }
        )
        url = f"{SEARCH_URL}?{params}"
        payload = self._fetch_json(url)
        if not payload:
            return []

        products: list[FoodProduct] = []
        for item in payload.get("hits", []):
            parsed = self._parse_search_hit(item)
            if parsed is not None:
                products.append(parsed)
        return products

    def _search_legacy(self, search_terms: str) -> list[FoodProduct]:
        params = urllib.parse.urlencode(
            {
                "search_terms": search_terms,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": self.page_size,
            }
        )
        url = f"{LEGACY_SEARCH_URL}?{params}"
        payload = self._fetch_json(url)
        if not payload:
            return []

        products: list[FoodProduct] = []
        for item in payload.get("products", []):
            parsed = self._parse_legacy_product(item)
            if parsed is not None:
                products.append(parsed)
        return products

    def _fetch_json(self, url: str) -> dict[str, Any] | None:
        def _request() -> dict[str, Any]:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))

        try:
            return with_retries(_request, label="open_food_facts", attempts=LLM_RETRY_ATTEMPTS)
        except RuntimeError:
            return None

    @staticmethod
    def _parse_search_hit(item: dict[str, Any]) -> FoodProduct | None:
        name = (
            item.get("product_name")
            or item.get("product_name_en")
            or item.get("generic_name")
            or ""
        ).strip()
        if not name:
            return None

        nutriments = item.get("nutriments") or {}
        brand = item.get("brands")
        if isinstance(brand, list):
            brand = ", ".join(brand)

        return FoodProduct(
            name=name,
            brand=str(brand or "").strip(),
            serving_size=str(item.get("quantity") or item.get("serving_size") or "100g").strip(),
            kcal_100g=_to_float(nutriments.get("energy-kcal_100g")),
            protein_100g=_to_float(nutriments.get("proteins_100g")),
            carbs_100g=_to_float(nutriments.get("carbohydrates_100g")),
            fat_100g=_to_float(nutriments.get("fat_100g")),
            barcode=str(item.get("code") or ""),
        )

    @staticmethod
    def _parse_legacy_product(item: dict[str, Any]) -> FoodProduct | None:
        name = (item.get("product_name") or item.get("generic_name") or "").strip()
        if not name:
            return None

        nutriments = item.get("nutriments") or {}
        kcal = nutriments.get("energy-kcal_100g")
        if kcal is None and nutriments.get("energy_100g") is not None:
            kcal = round(float(nutriments["energy_100g"]) / 4.184, 1)

        return FoodProduct(
            name=name,
            brand=(item.get("brands") or "").strip(),
            serving_size=(item.get("serving_size") or "100g").strip(),
            kcal_100g=_to_float(kcal),
            protein_100g=_to_float(nutriments.get("proteins_100g")),
            carbs_100g=_to_float(nutriments.get("carbohydrates_100g")),
            fat_100g=_to_float(nutriments.get("fat_100g")),
            barcode=str(item.get("code") or ""),
        )

    def retrieve_context(self, query: str) -> tuple[str, bool]:
        """
        Search Open Food Facts for a user query.

        Returns:
            (formatted_context, found_results)
        """
        if not self.is_food_query(query):
            return "", False

        search_terms = self.extract_search_terms(query)
        products = self.search(search_terms)
        if not products:
            return "", False

        lines = [product.to_context_line() for product in products]
        return "\n".join(lines), True


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None
