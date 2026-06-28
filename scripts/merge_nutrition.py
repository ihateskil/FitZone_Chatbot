import json, sys

# Load existing curated nutrition
with open('knowledge/nutrition.json', 'r', encoding='utf-8') as f:
    existing = json.load(f)

# Load USDA foods
with open('knowledge/usda_foods.json', 'r', encoding='utf-8') as f:
    usda = json.load(f)

# Build lookup by lowercase name
existing_lookup = {}
for e in existing:
    key = e['name'].lower().strip()
    existing_lookup[key] = e

# Merge: keep curated first, add USDA foods not already present
merged = list(existing)
added = 0
for u in usda:
    key = u['name'].lower().strip()
    if key not in existing_lookup:
        merged.append(u)
        existing_lookup[key] = u
        added += 1

# Category breakdown
cats = {}
for f in merged:
    cats[f.get('category','Other')] = cats.get(f.get('category','Other'), 0) + 1

print(f"Existing curated: {len(existing)}")
print(f"USDA new: {len(usda)}")
print(f"Added to merged: {added}")
print(f"Total merged: {len(merged)}")
print(f"\nCategory breakdown:")
for c, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}")

# Save merged
with open('knowledge/nutrition.json', 'w', encoding='utf-8') as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
print(f"\nSaved to knowledge/nutrition.json")

# Cleanup temp file
import os
os.remove('knowledge/usda_foods.json')
print("Removed temp usda_foods.json")
