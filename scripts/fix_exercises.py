"""Fix exercise categorization errors and duplicate entries in exercises.json."""
import json

with open("knowledge/exercises.json", encoding="utf-8") as f:
    data = json.load(f)

# ---- 1. Fix miscategorized exercises ----
# Format: (exact_name_match, correct_category)
CATEGORY_FIXES = {
    # Currently Abs but should be other categories
    "Biceps with TRX": "Arms",
    "Kettlebell Swing": "Shoulders",
    "TRX Rows": "Back",
    "Box squat": "Legs",
    "Reverse-grip pull-ups": "Back",
    "One armed push-ups": "Chest",
    "Mountain climbers": "Cardio",
    # Currently Chest but should be other categories
    "Overhead Press": "Shoulders",
    "Power Clean": "Legs",
    "Inverted Rows": "Back",
    "Burpees": "Cardio",
    "4-count burpees": "Cardio",
}

fix_count = 0
for entry in data:
    name = entry.get("name", "")
    if name in CATEGORY_FIXES:
        correct = CATEGORY_FIXES[name]
        if entry.get("category") != correct:
            entry["category"] = correct
            fix_count += 1
            print(f"  Fixed '{name}': {entry.get('category')} -> {correct}")

print(f"\nFixed {fix_count} categorizations")

# ---- 2. Handle duplicate names ----
# Keep the entry with more data (non-empty muscles, more instructions)
from collections import defaultdict

by_name = defaultdict(list)
for i, entry in enumerate(data):
    by_name[entry.get("name", "")].append(i)

dup_count = 0
indices_to_remove = set()
for name, indices in by_name.items():
    if len(indices) <= 1:
        continue
    # Score each entry: +1 for non-empty target_muscles, +1 for synergists, +1 for equipment, +1 for instructions
    scored = []
    for idx in indices:
        e = data[idx]
        score = 0
        if e.get("target_muscles"): score += 2
        if e.get("synergists"): score += 1
        if e.get("equipment") and any(eq.strip() for eq in e["equipment"] if isinstance(eq, str)): score += 1
        if e.get("instructions") and len(e["instructions"]) > 20: score += 1
        scored.append((score, idx))
    scored.sort(reverse=True)
    # Keep the best one, remove rest
    for score, idx in scored[1:]:
        indices_to_remove.add(idx)
        dup_count += 1
        print(f"  Removing duplicate '{name}' at index {idx} (score {score})")

# Remove from highest index to lowest to preserve indices
for idx in sorted(indices_to_remove, reverse=True):
    del data[idx]

print(f"\nRemoved {dup_count} duplicate entries")
print(f"Total remaining: {len(data)}")

with open("knowledge/exercises.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Saved exercises.json")
