"""
Nutrition data ingestion script for FitZone.
Downloads and normalizes USDA FoodData Central SR Legacy data
and Open Food Facts data into knowledge/nutrition.json and knowledge/nutrition.txt

USDA Source: https://fdc.nal.usda.gov/download-datasets.html (SR Legacy CSV, public domain)
Open Food Facts: https://world.openfoodfacts.org/data (Open Database License)
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

KNOWLEDGE_DIR = BASE_DIR / "knowledge"
NUTRITION_JSON = KNOWLEDGE_DIR / "nutrition.json"
NUTRITION_TXT = KNOWLEDGE_DIR / "nutrition.txt"

USER_AGENT = "FitZone-Chatbot/1.0 (fitness-nutrition-assistant)"
USDA_API_KEY = os.getenv("USDA_API_KEY", "")


class NutritionEntry:
    """A single nutrition data entry."""

    def __init__(
        self,
        name: str,
        source: str,
        category: str,
        serving_size: str,
        kcal_100g: float | None = None,
        protein_100g: float | None = None,
        carbs_100g: float | None = None,
        fat_100g: float | None = None,
        fiber_100g: float | None = None,
        sugar_100g: float | None = None,
        sodium_mg_100g: float | None = None,
    ) -> None:
        self.name = name
        self.source = source
        self.category = category
        self.serving_size = serving_size
        self.kcal_100g = kcal_100g
        self.protein_100g = protein_100g
        self.carbs_100g = carbs_100g
        self.fat_100g = fat_100g
        self.fiber_100g = fiber_100g
        self.sugar_100g = sugar_100g
        self.sodium_mg_100g = sodium_mg_100g

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "category": self.category,
            "serving_size": self.serving_size,
            "kcal_100g": self.kcal_100g,
            "protein_100g": self.protein_100g,
            "carbs_100g": self.carbs_100g,
            "fat_100g": self.fat_100g,
            "fiber_100g": self.fiber_100g,
            "sugar_100g": self.sugar_100g,
            "sodium_mg_100g": self.sodium_mg_100g,
        }

    def to_text_block(self) -> str:
        """Format as a text block for TF-IDF retrieval."""
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


def _to_float(value: Any) -> float | None:
    """Safely convert a value to float."""
    if value is None or value == "":
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def build_static_nutrition_db() -> list[NutritionEntry]:
    """
    Build a comprehensive static nutrition database from curated data.
    This covers the most common foods users ask about, ensuring the
    knowledge base is always populated even without internet access.
    """
    entries: list[NutritionEntry] = []

    # === PROTEINS ===
    proteins = [
        ("Chicken breast, cooked", "curated", "Protein", "100g", 165, 31.0, 0.0, 3.6, 0.0, 0.0, 74),
        ("Chicken thigh, cooked", "curated", "Protein", "100g", 209, 26.0, 0.0, 10.9, 0.0, 0.0, 84),
        ("Ground beef 90% lean, cooked", "curated", "Protein", "100g", 215, 26.0, 0.0, 11.3, 0.0, 0.0, 75),
        ("Ground beef 80% lean, cooked", "curated", "Protein", "100g", 254, 25.0, 0.0, 16.2, 0.0, 0.0, 72),
        ("Salmon, Atlantic, cooked", "curated", "Protein", "100g", 208, 20.0, 0.0, 13.0, 0.0, 0.0, 59),
        ("Tuna, canned in water", "curated", "Protein", "100g", 116, 26.0, 0.0, 0.8, 0.0, 0.0, 338),
        ("Turkey breast, cooked", "curated", "Protein", "100g", 135, 30.0, 0.0, 1.0, 0.0, 0.0, 55),
        ("Egg, whole, large", "curated", "Protein", "50g", 143, 12.6, 0.7, 9.5, 0.0, 0.4, 142),
        ("Egg whites, raw", "curated", "Protein", "100g", 52, 10.9, 0.7, 0.2, 0.0, 0.7, 166),
        ("Pork tenderloin, cooked", "curated", "Protein", "100g", 143, 26.0, 0.0, 3.5, 0.0, 0.0, 48),
        ("Shrimp, cooked", "curated", "Protein", "100g", 99, 24.0, 0.2, 0.3, 0.0, 0.0, 111),
        ("Cod, cooked", "curated", "Protein", "100g", 82, 18.0, 0.0, 0.7, 0.0, 0.0, 54),
        ("Tilapia, cooked", "curated", "Protein", "100g", 128, 26.0, 0.0, 2.7, 0.0, 0.0, 56),
        ("Sardines, canned", "curated", "Protein", "100g", 208, 24.6, 0.0, 11.5, 0.0, 0.0, 307),
        ("Beef steak sirloin, cooked", "curated", "Protein", "100g", 206, 26.0, 0.0, 11.0, 0.0, 0.0, 57),
        ("Lamb lean, cooked", "curated", "Protein", "100g", 258, 25.0, 0.0, 16.5, 0.0, 0.0, 72),
        ("Bison ground, cooked", "curated", "Protein", "100g", 179, 20.0, 0.0, 10.0, 0.0, 0.0, 66),
        ("Venison, cooked", "curated", "Protein", "100g", 158, 30.0, 0.0, 3.2, 0.0, 0.0, 51),
    ]
    for data in proteins:
        entries.append(NutritionEntry(*data))

    # === DAIRY ===
    dairy = [
        ("Greek yogurt plain nonfat", "curated", "Dairy", "100g", 59, 10.0, 3.6, 0.4, 0.0, 3.6, 36),
        ("Greek yogurt plain whole milk", "curated", "Dairy", "100g", 97, 9.0, 4.0, 5.0, 0.0, 4.0, 35),
        ("Cottage cheese low-fat", "curated", "Dairy", "100g", 72, 11.0, 3.4, 1.0, 0.0, 3.4, 40),
        ("Milk whole", "curated", "Dairy", "100ml", 61, 3.2, 4.8, 3.3, 0.0, 5.1, 43),
        ("Milk 2%", "curated", "Dairy", "100ml", 50, 3.4, 5.0, 2.0, 0.0, 5.1, 44),
        ("Milk skim", "curated", "Dairy", "100ml", 34, 3.4, 5.0, 0.1, 0.0, 5.1, 42),
        ("Cheddar cheese", "curated", "Dairy", "100g", 403, 25.0, 1.3, 33.1, 0.0, 0.5, 621),
        ("Mozzarella cheese part-skim", "curated", "Dairy", "100g", 254, 24.0, 2.8, 15.9, 0.0, 1.0, 486),
        ("Whey protein powder", "curated", "Supplements", "100g", 400, 80.0, 8.0, 7.0, 0.0, 4.0, 150),
        ("Casein protein powder", "curated", "Supplements", "100g", 360, 78.0, 4.0, 2.0, 0.0, 3.0, 100),
    ]
    for data in dairy:
        entries.append(NutritionEntry(*data))

    # === CARBOHYDRATES / GRAINS ===
    grains = [
        ("White rice cooked", "curated", "Grains", "100g", 130, 2.7, 28.2, 0.3, 0.4, 0.0, 1),
        ("Brown rice cooked", "curated", "Grains", "100g", 123, 2.7, 25.6, 1.0, 1.6, 0.4, 4),
        ("Oats dry", "curated", "Grains", "100g", 389, 16.9, 66.3, 6.9, 10.6, 0.0, 2),
        ("Quinoa cooked", "curated", "Grains", "100g", 120, 4.4, 21.3, 1.9, 2.8, 0.9, 7),
        ("Whole wheat bread", "curated", "Grains", "100g", 247, 13.0, 41.3, 3.4, 7.0, 6.0, 400),
        ("White bread", "curated", "Grains", "100g", 265, 9.0, 49.0, 3.2, 2.7, 5.0, 491),
        ("Pasta cooked", "curated", "Grains", "100g", 131, 5.0, 25.0, 1.1, 1.8, 0.6, 1),
        ("Sweet potato cooked", "curated", "Vegetables", "100g", 90, 2.0, 20.7, 0.1, 3.3, 6.5, 36),
        ("Potato white baked", "curated", "Vegetables", "100g", 93, 2.5, 21.1, 0.1, 2.2, 1.2, 7),
        ("Corn cooked", "curated", "Vegetables", "100g", 96, 3.4, 21.0, 1.5, 2.4, 4.5, 1),
    ]
    for data in grains:
        entries.append(NutritionEntry(*data))

    # === FRUITS ===
    fruits = [
        ("Banana", "curated", "Fruits", "100g", 89, 1.1, 22.8, 0.3, 2.6, 12.2, 1),
        ("Apple with skin", "curated", "Fruits", "100g", 52, 0.3, 13.8, 0.2, 2.4, 10.4, 1),
        ("Blueberries", "curated", "Fruits", "100g", 57, 0.7, 14.5, 0.3, 2.4, 10.0, 1),
        ("Strawberries", "curated", "Fruits", "100g", 32, 0.7, 7.7, 0.3, 2.0, 4.9, 1),
        ("Orange", "curated", "Fruits", "100g", 47, 0.9, 11.8, 0.1, 2.4, 9.4, 0),
        ("Grapes", "curated", "Fruits", "100g", 69, 0.7, 18.1, 0.2, 0.9, 15.5, 2),
        ("Mango", "curated", "Fruits", "100g", 60, 0.8, 15.0, 0.4, 1.6, 13.7, 1),
        ("Pineapple", "curated", "Fruits", "100g", 50, 0.5, 13.1, 0.1, 1.4, 9.9, 1),
        ("Avocado", "curated", "Fruits", "100g", 160, 2.0, 8.5, 14.7, 6.7, 0.7, 7),
        ("Watermelon", "curated", "Fruits", "100g", 30, 0.6, 7.6, 0.2, 0.4, 6.2, 1),
    ]
    for data in fruits:
        entries.append(NutritionEntry(*data))

    # === VEGETABLES ===
    vegetables = [
        ("Broccoli cooked", "curated", "Vegetables", "100g", 35, 2.4, 7.2, 0.4, 3.3, 1.4, 41),
        ("Spinach raw", "curated", "Vegetables", "100g", 23, 2.9, 3.6, 0.4, 2.2, 0.4, 79),
        ("Kale raw", "curated", "Vegetables", "100g", 49, 4.3, 8.8, 0.9, 3.6, 2.3, 38),
        ("Bell pepper red raw", "curated", "Vegetables", "100g", 31, 1.0, 6.0, 0.3, 2.1, 4.2, 4),
        ("Carrots raw", "curated", "Vegetables", "100g", 41, 0.9, 9.6, 0.2, 2.8, 4.7, 69),
        ("Cucumber raw", "curated", "Vegetables", "100g", 15, 0.7, 3.6, 0.1, 0.5, 1.7, 2),
        ("Tomato raw", "curated", "Vegetables", "100g", 18, 0.9, 3.9, 0.2, 1.2, 2.6, 5),
        ("Onion raw", "curated", "Vegetables", "100g", 40, 1.1, 9.3, 0.1, 1.7, 4.2, 4),
        ("Mushrooms white raw", "curated", "Vegetables", "100g", 22, 3.1, 3.3, 0.3, 1.0, 2.0, 5),
        ("Asparagus cooked", "curated", "Vegetables", "100g", 22, 2.4, 4.0, 0.2, 2.1, 1.9, 14),
        ("Green beans cooked", "curated", "Vegetables", "100g", 35, 1.9, 7.9, 0.3, 3.4, 1.5, 4),
        ("Zucchini cooked", "curated", "Vegetables", "100g", 17, 1.2, 3.1, 0.3, 1.0, 2.5, 3),
    ]
    for data in vegetables:
        entries.append(NutritionEntry(*data))

    # === LEGUMES ===
    legumes = [
        ("Black beans cooked", "curated", "Legumes", "100g", 132, 8.9, 23.7, 0.5, 8.7, 0.3, 1),
        ("Kidney beans cooked", "curated", "Legumes", "100g", 127, 8.7, 22.8, 0.5, 7.4, 0.3, 1),
        ("Chickpeas cooked", "curated", "Legumes", "100g", 164, 8.9, 27.4, 2.6, 7.6, 4.8, 7),
        ("Lentils cooked", "curated", "Legumes", "100g", 116, 9.0, 20.1, 0.4, 7.9, 1.8, 2),
        ("Edamame cooked", "curated", "Legumes", "100g", 121, 11.9, 8.9, 5.2, 5.2, 2.2, 6),
        ("Pinto beans cooked", "curated", "Legumes", "100g", 143, 9.0, 26.2, 0.7, 9.0, 0.3, 1),
    ]
    for data in legumes:
        entries.append(NutritionEntry(*data))

    # === NUTS & SEEDS ===
    nuts = [
        ("Almonds raw", "curated", "Nuts & Seeds", "100g", 579, 21.2, 21.6, 49.9, 12.5, 4.4, 1),
        ("Walnuts raw", "curated", "Nuts & Seeds", "100g", 654, 15.2, 13.7, 65.2, 6.7, 2.6, 2),
        ("Peanuts raw", "curated", "Nuts & Seeds", "100g", 567, 25.8, 16.1, 49.2, 8.5, 4.0, 18),
        ("Peanut butter natural", "curated", "Nuts & Seeds", "100g", 588, 25.1, 20.0, 50.4, 6.0, 9.2, 17),
        ("Cashews raw", "curated", "Nuts & Seeds", "100g", 553, 18.2, 30.2, 43.9, 3.3, 5.9, 12),
        ("Chia seeds", "curated", "Nuts & Seeds", "100g", 486, 16.5, 42.1, 30.7, 34.4, 0.0, 16),
        ("Flax seeds ground", "curated", "Nuts & Seeds", "100g", 534, 18.3, 28.9, 42.2, 27.3, 1.6, 30),
        ("Pumpkin seeds", "curated", "Nuts & Seeds", "100g", 559, 30.2, 10.7, 49.1, 6.0, 1.4, 7),
        ("Sunflower seeds", "curated", "Nuts & Seeds", "100g", 584, 20.8, 20.0, 51.5, 8.6, 2.6, 9),
        ("Hemp seeds hulled", "curated", "Nuts & Seeds", "100g", 553, 31.6, 8.7, 48.8, 4.0, 1.5, 5),
    ]
    for data in nuts:
        entries.append(NutritionEntry(*data))

    # === FATS & OILS ===
    fats = [
        ("Olive oil extra virgin", "curated", "Fats & Oils", "100ml", 884, 0.0, 0.0, 100.0, 0.0, 0.0, 2),
        ("Coconut oil", "curated", "Fats & Oils", "100ml", 862, 0.0, 0.0, 100.0, 0.0, 0.0, 0),
        ("Butter unsalted", "curated", "Fats & Oils", "100g", 717, 0.9, 0.1, 81.1, 0.0, 0.1, 11),
        ("Ghee clarified butter", "curated", "Fats & Oils", "100g", 876, 0.0, 0.0, 99.5, 0.0, 0.0, 0),
    ]
    for data in fats:
        entries.append(NutritionEntry(*data))

    # === BEVERAGES ===
    beverages = [
        ("Coffee black", "curated", "Beverages", "100ml", 2, 0.1, 0.0, 0.0, 0.0, 0.0, 2),
        ("Green tea brewed", "curated", "Beverages", "100ml", 1, 0.0, 0.2, 0.0, 0.0, 0.0, 0),
        ("Orange juice fresh", "curated", "Beverages", "100ml", 45, 0.7, 10.4, 0.2, 0.2, 8.4, 1),
        ("Coconut water", "curated", "Beverages", "100ml", 19, 0.7, 3.7, 0.2, 1.1, 2.6, 25),
    ]
    for data in beverages:
        entries.append(NutritionEntry(*data))

    # === CONDIMENTS & MISC ===
    misc = [
        ("Honey", "curated", "Condiments", "100g", 304, 0.3, 82.4, 0.0, 0.2, 82.1, 4),
        ("Maple syrup", "curated", "Condiments", "100g", 260, 0.0, 67.0, 0.1, 0.0, 60.5, 12),
        ("Soy sauce", "curated", "Condiments", "100ml", 53, 8.1, 4.9, 0.1, 0.8, 0.4, 5493),
        ("Hot sauce", "curated", "Condiments", "100g", 12, 0.5, 2.0, 0.1, 0.3, 1.0, 1200),
        ("Tofu firm", "curated", "Protein", "100g", 144, 15.6, 2.8, 8.7, 0.3, 0.6, 14),
        ("Tempeh", "curated", "Protein", "100g", 192, 20.3, 7.6, 10.8, 0.0, 0.0, 9),
    ]
    for data in misc:
        entries.append(NutritionEntry(*data))

    return entries


def try_download_usda() -> list[NutritionEntry]:
    """
    Download USDA FoodData Central data via the live API.
    Uses the API key from USDA_API_KEY env var for higher rate limits.
    Falls back to SR Legacy ZIP if API fails.
    """
    entries: list[NutritionEntry] = []

    # Strategy 1: Live API (fast, uses key for higher rate limits)
    if USDA_API_KEY:
        print("Attempting USDA FoodData Central API download...")
        entries = _download_usda_api()
        if entries:
            return entries
        print("  API download returned no results, trying ZIP fallback...")

    # Strategy 2: SR Legacy ZIP (slow but comprehensive)
    print("Attempting USDA SR Legacy ZIP download...")
    entries = _download_usda_zip()
    return entries


def _download_usda_api() -> list[NutritionEntry]:
    """Download from the live USDA FDC API using the API key."""
    import time as _time

    entries: list[NutritionEntry] = []
    # Search for common food categories to build a diverse database
    search_terms = [
        "chicken", "beef", "salmon", "egg", "rice", "oatmeal",
        "banana", "apple", "broccoli", "sweet potato", "almonds",
        "greek yogurt", "cottage cheese", "whey protein", "pasta",
        "bread", "avocado", "olive oil", "peanut butter", "lentils",
        "tuna", "turkey", "pork", "shrimp", "tofu",
    ]

    for term in search_terms:
        try:
            url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={urllib.parse.quote(term)}&pageSize=5&api_key={USDA_API_KEY}"
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))

            for food in payload.get("foods", []):
                name = (food.get("description") or food.get("lowercaseDescription") or "").strip()
                if not name:
                    continue

                # Extract nutrients from the foods endpoint
                nutrients = {}
                for n in food.get("foodNutrients", []):
                    nid = n.get("nutrientId", n.get("nutrient", {}).get("id", ""))
                    val = n.get("value", n.get("amount", ""))
                    if nid and val:
                        try:
                            nutrients[str(nid)] = float(val)
                        except (ValueError, TypeError):
                            pass

                entry = NutritionEntry(
                    name=name,
                    source="USDA_FDC_API",
                    category=food.get("foodCategory", food.get("brandedFoodCategory", "General")),
                    serving_size="100g",
                    kcal_100g=nutrients.get("1008"),
                    protein_100g=nutrients.get("1003"),
                    carbs_100g=nutrients.get("1011") or nutrients.get("1005"),
                    fat_100g=nutrients.get("1004"),
                    fiber_100g=nutrients.get("1009") or nutrients.get("1079"),
                    sugar_100g=nutrients.get("1010") or nutrients.get("2000"),
                    sodium_mg_100g=nutrients.get("1093"),
                )
                entries.append(entry)

            _time.sleep(0.25)  # Rate limit: 4 requests/sec with API key

        except Exception as exc:
            print(f"  API search for '{term}' failed: {exc}")
            continue

    print(f"  Loaded {len(entries)} USDA entries via API")
    return entries


def _download_usda_zip() -> list[NutritionEntry]:
    """Fallback: download the SR Legacy ZIP file."""
    entries: list[NutritionEntry] = []

    try:
        url = "https://fdc.nal.usda.gov/fdc_downloads/SR-Legacy_2023-04-20.zip"
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        print(f"  Downloading from {url}...")
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            csv_name = None
            for name in zf.namelist():
                if "food" in name.lower() and name.endswith(".csv") and "nutrient" not in name.lower():
                    csv_name = name
                    break

            if csv_name is None:
                print("  WARNING: Could not find food CSV in USDA zip")
                return entries

            print(f"  Found CSV: {csv_name}")
            with zf.open(csv_name) as csvfile:
                reader = csv.DictReader(io.TextIOWrapper(csvfile, encoding="utf-8"))

                # Build nutrient lookup from food_nutrient.csv
                nutrient_csv = None
                for name in zf.namelist():
                    if "food_nutrient" in name.lower() and name.endswith(".csv"):
                        nutrient_csv = name
                        break

                nutrient_map: dict[str, dict[str, float]] = {}
                if nutrient_csv:
                    with zf.open(nutrient_csv) as nf:
                        nreader = csv.DictReader(io.TextIOWrapper(nf, encoding="utf-8"))
                        for row in nreader:
                            fid = row.get("fdc_id", row.get("food_id", ""))
                            nid = row.get("nutrient_id", "")
                            val = row.get("amount", row.get("value", ""))
                            if fid and nid and val:
                                nutrient_map.setdefault(fid, {})[nid] = float(val)

                # Nutrient IDs in SR Legacy:
                # 1003 = Protein, 1004 = Total Fat, 1008 = Energy (kcal)
                # 1009 = Fiber, 1010 = Sugar, 1011 = Carbs
                # 1093 = Sodium
                count = 0
                for row in reader:
                    fid = row.get("fdc_id", row.get("id", ""))
                    name = row.get("description", row.get("name", "")).strip()
                    if not name:
                        continue

                    nutrients = nutrient_map.get(fid, {})
                    entry = NutritionEntry(
                        name=name,
                        source="USDA_FDC",
                        category=row.get("food_category", row.get("category", "General")),
                        serving_size="100g",
                        kcal_100g=nutrients.get("1008"),
                        protein_100g=nutrients.get("1003"),
                        carbs_100g=nutrients.get("1011"),
                        fat_100g=nutrients.get("1004"),
                        fiber_100g=nutrients.get("1009"),
                        sugar_100g=nutrients.get("1010"),
                        sodium_mg_100g=nutrients.get("1093"),
                    )
                    entries.append(entry)
                    count += 1
                    if count >= 5000:  # Cap at 5000 to keep index lean
                        break

                print(f"  Loaded {count} USDA food entries from ZIP")

    except Exception as exc:
        print(f"  USDA ZIP download failed: {exc}")
        print("  Falling back to curated database only")

    return entries


def try_download_openfoodfacts() -> list[NutritionEntry]:
    """
    Attempt to download a sample of Open Food Facts data.
    Returns empty list if download fails.
    """
    entries: list[NutritionEntry] = []
    print("Attempting Open Food Facts download...")

    try:
        # Use the search API to get popular products
        search_url = "https://world.openfoodfacts.org/cgi/search.pl?search_terms=protein&search_simple=1&action=process&json=1&page_size=100"
        request = urllib.request.Request(search_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))

        for item in payload.get("products", []):
            name = (item.get("product_name") or item.get("product_name_en") or "").strip()
            if not name:
                continue
            nutriments = item.get("nutriments") or {}
            entry = NutritionEntry(
                name=name,
                source="OpenFoodFacts",
                category=item.get("categories", "General"),
                serving_size=str(item.get("serving_size") or "100g"),
                kcal_100g=_to_float(nutriments.get("energy-kcal_100g")),
                protein_100g=_to_float(nutriments.get("proteins_100g")),
                carbs_100g=_to_float(nutriments.get("carbohydrates_100g")),
                fat_100g=_to_float(nutriments.get("fat_100g")),
                fiber_100g=_to_float(nutriments.get("fiber_100g")),
                sugar_100g=_to_float(nutriments.get("sugars_100g")),
                sodium_mg_100g=_to_float(nutriments.get("sodium_100g")),
            )
            entries.append(entry)

        print(f"  Loaded {len(entries)} Open Food Facts entries")

    except Exception as exc:
        print(f"  Open Food Facts download failed: {exc}")
        print("  Skipping OFF data")

    return entries


def ingest_nutrition() -> tuple[int, dict[str, int]]:
    """
    Main ingestion pipeline.
    Downloads from USDA + OFF, merges with curated data, writes JSON + TXT.
    Returns (total_count, category_breakdown).
    """
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    # Start with curated data (always available)
    all_entries = build_static_nutrition_db()
    print(f"Curated database: {len(all_entries)} entries")

    # Try to augment with live data
    usda_entries = try_download_usda()
    all_entries.extend(usda_entries)

    off_entries = try_download_openfoodfacts()
    all_entries.extend(off_entries)

    # Deduplicate by name (case-insensitive)
    seen: dict[str, NutritionEntry] = {}
    for entry in all_entries:
        key = entry.name.lower().strip()
        if key not in seen:
            seen[key] = entry
    deduped = list(seen.values())

    # Write JSON
    json_data = [e.to_dict() for e in deduped]
    NUTRITION_JSON.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write TXT (for TF-IDF retrieval)
    text_blocks = []
    for entry in deduped:
        text_blocks.append(entry.to_text_block())
    NUTRITION_TXT.write_text("\n\n----\n\n".join(text_blocks), encoding="utf-8")

    # Compute stats
    categories: dict[str, int] = {}
    field_coverage = {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0}
    for entry in deduped:
        categories[entry.category] = categories.get(entry.category, 0) + 1
        if entry.kcal_100g is not None:
            field_coverage["kcal"] += 1
        if entry.protein_100g is not None:
            field_coverage["protein"] += 1
        if entry.carbs_100g is not None:
            field_coverage["carbs"] += 1
        if entry.fat_100g is not None:
            field_coverage["fat"] += 1

    # Print summary
    print()
    print("=" * 60)
    print("NUTRITION DATABASE INGESTION COMPLETE")
    print("=" * 60)
    print(f"Total entries: {len(deduped)}")
    print(f"\nCategory breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print(f"\nField coverage:")
    for field, count in field_coverage.items():
        pct = (count / len(deduped) * 100) if deduped else 0
        print(f"  {field}: {count}/{len(deduped)} ({pct:.1f}%)")
    print(f"\nFiles written:")
    print(f"  {NUTRITION_JSON}")
    print(f"  {NUTRITION_TXT}")
    print("=" * 60)

    return len(deduped), categories


if __name__ == "__main__":
    count, breakdown = ingest_nutrition()
    print(f"\nDone. {count} total nutrition entries available.")
