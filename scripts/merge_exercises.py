import json, sys

with open('knowledge/exercises.json', 'r', encoding='utf-8') as f:
    current = json.load(f)

with open('knowledge/free_exercises.json', 'r', encoding='utf-8') as f:
    free = json.load(f)

# Map category
def map_cat(cat):
    c = cat.lower() if cat else ''
    if 'strength' in c: return 'Strength'
    if 'cardio' in c or 'plyo' in c: return 'Cardio'
    if 'stretch' in c or 'flexibility' in c: return 'Flexibility'
    if 'warm' in c or 'cool' in c: return 'Warm-up'
    return 'Strength'

# Build set of existing names for dedup
existing_names = set()
for e in current:
    existing_names.add(e['name'].lower().strip())

# Map free-exercise-db entries
added = 0
for f in free:
    name = f.get('name', '').strip()
    if not name or name.lower().strip() in existing_names:
        continue
    existing_names.add(name.lower().strip())
    entry = {
        'name': name,
        'category': map_cat(f.get('category')),
        'target_muscles': [m.strip() for m in f.get('primaryMuscles', []) if m.strip()],
        'synergists': [m.strip() for m in f.get('secondaryMuscles', []) if m.strip()],
        'equipment': [f.get('equipment', 'bodyweight').strip()] if f.get('equipment') else [],
        'instructions': f.get('instructions', []),
        'cues': [],
        'source': 'free-exercise-db',
    }
    current.append(entry)
    added += 1

cat_counts = {}
for e in current:
    cat_counts[e['category']] = cat_counts.get(e['category'], 0) + 1

print(f"Current exercises: {len(current) - added} (before merge)")
print(f"Free-exercise-db: {len(free)}")
print(f"Added (new unique): {added}")
print(f"Total after merge: {len(current)}")
print(f"\nCategory breakdown:")
for c, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}")

with open('knowledge/exercises.json', 'w', encoding='utf-8') as f:
    json.dump(current, f, indent=2, ensure_ascii=False)

import os
os.remove('knowledge/free_exercises.json')
print("\nSaved exercises.json (removed temp free_exercises.json)")
