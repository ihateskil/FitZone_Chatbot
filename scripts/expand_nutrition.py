"""Expand nutrition.json with 100+ missing common foods."""
import json

with open("knowledge/nutrition.json", encoding="utf-8") as f:
    existing = json.load(f)

existing_names = {e["name"].lower().strip() for e in existing}

# (name, category, kcal, protein, carbs, fat, fiber, sugar, sodium_mg)
NEW_FOODS = [
    # ---- MISSING VEGETABLES ----
    ("Cauliflower cooked", "Vegetables", 25, 1.8, 5.0, 0.3, 2.5, 1.9, 18),
    ("Brussels sprouts cooked", "Vegetables", 43, 3.4, 9.0, 0.3, 3.8, 2.2, 25),
    ("Cabbage red raw", "Vegetables", 31, 1.4, 7.4, 0.2, 2.1, 3.8, 27),
    ("Cabbage green raw", "Vegetables", 25, 1.3, 5.8, 0.1, 2.5, 3.2, 18),
    ("Bok choy cooked", "Vegetables", 12, 1.6, 1.8, 0.2, 1.0, 1.0, 52),
    ("Celery raw", "Vegetables", 16, 0.7, 3.0, 0.2, 1.6, 1.8, 80),
    ("Beetroot cooked", "Vegetables", 44, 1.7, 10.0, 0.2, 2.0, 8.0, 78),
    ("Eggplant cooked", "Vegetables", 35, 0.8, 8.7, 0.2, 2.5, 3.2, 1),
    ("Artichoke cooked", "Vegetables", 53, 2.9, 11.4, 0.3, 5.7, 1.1, 70),
    ("Okra cooked", "Vegetables", 22, 1.9, 4.5, 0.1, 2.0, 2.4, 3),
    ("Peas green cooked", "Vegetables", 84, 5.4, 15.6, 0.2, 5.5, 5.9, 3),
    ("Arugula raw", "Vegetables", 25, 2.6, 3.7, 0.7, 1.6, 2.1, 27),
    ("Lettuce romaine raw", "Vegetables", 17, 1.2, 3.3, 0.3, 2.1, 1.2, 8),
    ("Lettuce iceberg raw", "Vegetables", 14, 0.9, 3.0, 0.1, 1.2, 2.0, 10),
    ("Garlic raw", "Vegetables", 149, 6.4, 33.1, 0.5, 2.1, 1.0, 17),
    ("Ginger root raw", "Vegetables", 80, 1.8, 17.8, 0.8, 2.0, 1.7, 13),
    ("Jalapeno pepper raw", "Vegetables", 29, 0.9, 6.5, 0.4, 2.8, 4.1, 3),
    ("Snow peas cooked", "Vegetables", 42, 3.0, 7.1, 0.2, 2.7, 4.0, 4),
    ("Radish raw", "Vegetables", 16, 0.7, 3.4, 0.1, 1.6, 1.9, 39),
    ("Turnip cooked", "Vegetables", 22, 0.7, 5.1, 0.1, 2.0, 3.0, 16),

    # ---- MISSING FRUITS ----
    ("Kiwi raw", "Fruits", 61, 1.1, 14.7, 0.5, 3.0, 9.0, 3),
    ("Papaya raw", "Fruits", 43, 0.5, 10.8, 0.3, 1.7, 7.8, 8),
    ("Cherries sweet raw", "Fruits", 63, 1.1, 16.0, 0.2, 2.1, 12.8, 0),
    ("Peach raw", "Fruits", 39, 0.9, 9.5, 0.3, 1.5, 8.4, 0),
    ("Plum raw", "Fruits", 46, 0.7, 11.4, 0.3, 1.4, 9.9, 0),
    ("Raspberries raw", "Fruits", 52, 1.2, 11.9, 0.7, 6.5, 4.4, 1),
    ("Blackberries raw", "Fruits", 43, 1.4, 9.6, 0.5, 5.3, 4.9, 1),
    ("Cranberries dried", "Fruits", 308, 0.2, 82.4, 1.1, 4.6, 65.0, 3),
    ("Raisins seedless", "Fruits", 299, 3.1, 79.3, 0.5, 3.7, 59.2, 11),
    ("Dates medjool", "Fruits", 277, 1.8, 75.0, 0.2, 6.7, 66.5, 1),
    ("Lemon raw", "Fruits", 29, 1.1, 9.3, 0.3, 2.8, 2.5, 2),
    ("Lime raw", "Fruits", 30, 0.7, 10.5, 0.2, 2.8, 1.7, 2),
    ("Grapefruit raw", "Fruits", 42, 0.8, 10.7, 0.1, 1.6, 6.9, 0),
    ("Pear raw", "Fruits", 57, 0.4, 15.2, 0.1, 3.1, 9.8, 1),
    ("Cantaloupe raw", "Fruits", 34, 0.8, 8.2, 0.2, 0.9, 7.9, 16),
    ("Honeydew melon raw", "Fruits", 36, 0.5, 9.1, 0.1, 0.8, 8.1, 18),
    ("Coconut meat raw", "Fruits", 354, 3.3, 15.2, 33.5, 9.0, 6.2, 20),
    ("Avocado oil", "Fats & Oils", 884, 0.0, 0.0, 100.0, 0.0, 0.0, 0),

    # ---- MISSING PROTEINS ----
    ("Bacon cooked", "Protein", 541, 37.0, 1.4, 42.0, 0.0, 0.0, 1478),
    ("Turkey bacon cooked", "Protein", 379, 29.0, 2.0, 29.0, 0.0, 0.0, 1600),
    ("Chicken wing cooked", "Protein", 222, 22.5, 0.0, 14.4, 0.0, 0.0, 80),
    ("Chicken liver cooked", "Protein", 167, 24.6, 1.1, 6.4, 0.0, 0.0, 60),
    ("Beef liver cooked", "Protein", 192, 29.1, 5.1, 6.3, 0.0, 0.0, 60),
    ("Beef ribeye steak cooked", "Protein", 291, 24.0, 0.0, 21.0, 0.0, 0.0, 70),
    ("Ground turkey 93% lean cooked", "Protein", 209, 27.0, 0.0, 11.0, 0.0, 0.0, 80),
    ("Italian sausage cooked", "Protein", 344, 16.0, 2.0, 30.0, 0.0, 0.0, 900),
    ("Pepperoni", "Protein", 504, 20.4, 1.2, 46.0, 0.0, 0.5, 1600),
    ("Ham sliced deli", "Protein", 145, 20.0, 1.5, 6.5, 0.0, 1.0, 1100),
    ("Prosciutto", "Protein", 269, 27.0, 0.3, 17.0, 0.0, 0.0, 1930),
    ("Salami", "Protein", 407, 22.0, 1.5, 34.0, 0.0, 0.5, 1740),
    ("Mackerel cooked", "Protein", 262, 23.9, 0.0, 17.8, 0.0, 0.0, 70),
    ("Trout cooked", "Protein", 190, 24.0, 0.0, 9.7, 0.0, 0.0, 55),
    ("Herring pickled", "Protein", 217, 15.4, 7.5, 14.0, 0.0, 7.0, 870),
    ("Clams cooked", "Protein", 148, 25.6, 5.1, 1.9, 0.0, 0.0, 120),
    ("Mussels cooked", "Protein", 172, 23.8, 7.4, 4.5, 0.0, 0.0, 370),
    ("Scallops cooked", "Protein", 137, 23.8, 6.3, 1.0, 0.0, 0.0, 660),
    ("Lobster cooked", "Protein", 89, 18.8, 1.3, 0.9, 0.0, 0.0, 410),
    ("Crab cooked", "Protein", 87, 18.1, 0.0, 1.5, 0.0, 0.0, 560),
    ("Duck breast cooked", "Protein", 200, 24.0, 0.0, 11.0, 0.0, 0.0, 85),
    ("Lamb chop cooked", "Protein", 286, 23.0, 0.0, 21.0, 0.0, 0.0, 72),
    ("Venison cooked", "Protein", 190, 30.0, 0.0, 7.0, 0.0, 0.0, 55),
    ("Bison ground cooked", "Protein", 217, 24.0, 0.0, 13.0, 0.0, 0.0, 75),

    # ---- MISSING DAIRY ----
    ("Parmesan cheese grated", "Dairy", 431, 38.0, 4.1, 29.0, 0.0, 0.1, 1529),
    ("Feta cheese", "Dairy", 264, 14.2, 4.0, 21.3, 0.0, 4.0, 1116),
    ("Goat cheese soft", "Dairy", 264, 18.0, 0.0, 21.0, 0.0, 0.0, 415),
    ("Cream cheese", "Dairy", 342, 6.0, 4.0, 34.0, 0.0, 3.0, 320),
    ("Ricotta cheese part-skim", "Dairy", 156, 11.4, 5.1, 10.0, 0.0, 0.3, 126),
    ("Swiss cheese", "Dairy", 380, 27.0, 1.4, 30.0, 0.0, 0.0, 202),
    ("Sour cream", "Dairy", 193, 2.4, 4.6, 19.0, 0.0, 0.1, 40),
    ("Heavy cream", "Dairy", 340, 2.8, 2.8, 36.0, 0.0, 0.1, 38),
    ("Half and half", "Dairy", 131, 3.0, 4.3, 11.5, 0.0, 0.1, 61),
    ("Ice cream vanilla", "Dairy", 207, 3.5, 23.6, 11.0, 0.0, 21.2, 72),
    ("Kefir lowfat", "Dairy", 41, 3.8, 4.8, 0.9, 0.0, 4.0, 50),
    ("Butter unsalted", "Dairy", 717, 0.9, 0.1, 81.1, 0.0, 0.0, 2),

    # ---- MISSING GRAINS ----
    ("Couscous cooked", "Grains", 112, 3.8, 23.2, 0.2, 1.4, 0.1, 5),
    ("Barley cooked", "Grains", 123, 2.3, 28.2, 0.4, 3.8, 0.3, 3),
    ("Buckwheat cooked", "Grains", 92, 3.4, 19.9, 0.6, 2.7, 0.9, 4),
    ("Millet cooked", "Grains", 119, 3.5, 23.7, 1.0, 1.3, 0.1, 2),
    ("Corn tortilla", "Grains", 218, 5.7, 44.6, 2.5, 4.5, 1.2, 45),
    ("Flour tortilla", "Grains", 300, 7.5, 49.0, 7.0, 2.5, 2.0, 640),
    ("Rice cakes", "Grains", 386, 7.9, 82.0, 2.8, 4.2, 0.4, 28),
    ("Granola", "Grains", 471, 10.0, 64.0, 20.0, 5.0, 20.0, 20),
    ("Oatmeal cooked", "Grains", 71, 2.5, 12.3, 1.5, 1.7, 0.3, 4),
    ("Egg noodles cooked", "Grains", 138, 5.0, 25.0, 2.1, 1.2, 0.4, 10),

    # ---- MISSING LEGUMES ----
    ("Hummus", "Legumes", 166, 7.9, 14.3, 9.6, 4.0, 0.8, 379),
    ("Soybeans cooked", "Legumes", 173, 16.6, 9.9, 9.0, 6.0, 3.0, 1),
    ("Mung beans cooked", "Legumes", 127, 8.3, 23.1, 0.4, 7.6, 0.4, 4),
    ("Navy beans cooked", "Legumes", 140, 8.2, 26.1, 0.6, 10.5, 0.4, 2),

    # ---- MISSING NUTS & SEEDS ----
    ("Pecans raw", "Nuts & Seeds", 691, 9.2, 13.9, 72.0, 9.6, 4.0, 0),
    ("Macadamia nuts raw", "Nuts & Seeds", 718, 7.9, 13.8, 75.8, 8.6, 4.6, 4),
    ("Pistachios raw", "Nuts & Seeds", 560, 20.2, 27.2, 45.3, 10.6, 7.7, 1),
    ("Brazil nuts raw", "Nuts & Seeds", 659, 14.3, 11.7, 67.1, 7.5, 2.3, 3),
    ("Pine nuts raw", "Nuts & Seeds", 673, 13.7, 13.1, 68.4, 3.7, 3.6, 2),
    ("Tahini", "Nuts & Seeds", 595, 17.0, 21.2, 53.8, 4.6, 0.5, 62),
    ("Sesame seeds", "Nuts & Seeds", 573, 17.7, 23.5, 49.7, 11.8, 0.3, 11),
    ("Almond butter", "Nuts & Seeds", 614, 21.0, 18.8, 55.0, 8.0, 3.0, 7),
    ("Cashew butter", "Nuts & Seeds", 587, 17.6, 27.6, 49.4, 3.0, 5.0, 15),
    ("Coconut shredded unsweetened", "Nuts & Seeds", 660, 6.9, 23.7, 64.5, 16.3, 7.4, 16),

    # ---- MISSING FATS & OILS ----
    ("Sesame oil", "Fats & Oils", 884, 0.0, 0.0, 100.0, 0.0, 0.0, 0),
    ("Canola oil", "Fats & Oils", 884, 0.0, 0.0, 100.0, 0.0, 0.0, 0),
    ("Vegetable oil", "Fats & Oils", 884, 0.0, 0.0, 100.0, 0.0, 0.0, 0),
    ("Peanut oil", "Fats & Oils", 884, 0.0, 0.0, 100.0, 0.0, 0.0, 0),
    ("Lard", "Fats & Oils", 902, 0.0, 0.0, 100.0, 0.0, 0.0, 0),
    ("Mayonnaise", "Fats & Oils", 724, 1.0, 0.6, 79.0, 0.0, 0.6, 635),

    # ---- MISSING CONDIMENTS ----
    ("Ketchup", "Condiments", 101, 1.0, 27.4, 0.1, 0.3, 21.3, 907),
    ("Yellow mustard", "Condiments", 66, 3.7, 5.8, 3.3, 1.5, 0.9, 1135),
    ("Dijon mustard", "Condiments", 108, 6.0, 5.0, 7.0, 2.0, 1.0, 1580),
    ("BBQ sauce", "Condiments", 135, 0.7, 33.0, 0.4, 0.5, 24.0, 820),
    ("Ranch dressing", "Condiments", 440, 1.5, 3.5, 47.0, 0.2, 2.0, 690),
    ("Italian dressing", "Condiments", 290, 0.5, 5.0, 30.0, 0.0, 4.0, 980),
    ("Salsa", "Condiments", 36, 1.5, 7.0, 0.2, 2.0, 4.0, 530),
    ("Apple cider vinegar", "Condiments", 22, 0.0, 0.9, 0.0, 0.0, 0.4, 5),
    ("Balsamic vinegar", "Condiments", 88, 0.5, 17.0, 0.0, 0.0, 15.0, 23),

    # ---- MISSING BEVERAGES ----
    ("Almond milk unsweetened", "Beverages", 17, 0.5, 0.6, 1.1, 0.0, 0.4, 77),
    ("Soy milk unsweetened", "Beverages", 33, 2.9, 1.7, 1.6, 0.4, 0.6, 51),
    ("Oat milk", "Beverages", 47, 1.0, 7.0, 1.5, 0.5, 4.0, 80),
    ("Coconut milk beverage", "Beverages", 23, 0.2, 2.6, 1.1, 0.2, 2.0, 50),
    ("Coca-Cola regular", "Beverages", 42, 0.0, 10.6, 0.0, 0.0, 10.6, 4),
    ("Diet Coke", "Beverages", 0, 0.0, 0.0, 0.0, 0.0, 0.0, 10),
    ("Gatorade", "Beverages", 24, 0.0, 6.0, 0.0, 0.0, 5.6, 50),
    ("Beer regular", "Beverages", 43, 0.5, 3.6, 0.0, 0.0, 0.3, 4),
    ("Red wine", "Beverages", 85, 0.1, 2.6, 0.0, 0.0, 0.6, 4),

    # ---- MISSING SUPPLEMENTS ----
    ("Creatine monohydrate", "Supplements", 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0),
    ("Fish oil omega-3 supplement", "Supplements", 900, 0.0, 0.0, 100.0, 0.0, 0.0, 0),
    ("Multivitamin", "Supplements", 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0),
    ("Vitamin D supplement", "Supplements", 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0),
    ("Magnesium supplement", "Supplements", 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0),
    ("BCAA supplement", "Supplements", 0, 100.0, 0.0, 0.0, 0.0, 0.0, 0),
    ("Collagen peptides", "Supplements", 350, 90.0, 0.0, 0.0, 0.0, 0.0, 0),
    ("Pre-workout supplement", "Supplements", 10, 0.0, 1.5, 0.0, 0.0, 0.0, 20),

    # ---- MISSING MEAL COMPONENTS ----
    ("Pizza cheese pepperoni frozen", "Protein", 276, 12.0, 26.0, 14.0, 1.5, 4.0, 650),
    ("Chicken breast breaded cooked", "Protein", 239, 18.0, 10.0, 14.0, 0.5, 1.0, 400),
    ("Beef burger patty cooked", "Protein", 250, 25.0, 0.0, 17.0, 0.0, 0.0, 75),
    ("Hot dog beef", "Protein", 290, 10.0, 3.0, 27.0, 0.0, 1.5, 1150),
    ("Turkey burger patty cooked", "Protein", 210, 22.0, 0.0, 13.0, 0.0, 0.0, 400),
]

added_count = 0
for food in NEW_FOODS:
    name, category, kcal, protein, carbs, fat, fiber, sugar, sodium = food
    key = name.lower().strip()
    if key in existing_names:
        continue
    existing.append({
        "name": name,
        "source": "curated",
        "category": category,
        "serving_size": "100g",
        "kcal_100g": kcal,
        "protein_100g": protein,
        "carbs_100g": carbs,
        "fat_100g": fat,
        "fiber_100g": fiber,
        "sugar_100g": sugar,
        "sodium_mg_100g": sodium,
    })
    existing_names.add(key)
    added_count += 1

with open("knowledge/nutrition.json", "w", encoding="utf-8") as f:
    json.dump(existing, f, indent=2, ensure_ascii=False)

print(f"Added {added_count} new foods to nutrition.json")
print(f"Total: {len(existing)} entries")

# Show category breakdown
from collections import Counter
cats = Counter(e["category"] for e in existing)
for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count}")
