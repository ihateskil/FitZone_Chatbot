import requests, json, sys, time

API_KEY = 'S77StevMvCwvafDVvUfWwPKWlcD5bGdyZ1xIlI9N'
BASE = 'https://api.nal.usda.gov/fdc/v1'

def categorize_food(desc):
    d = desc.lower()
    meat = ['chicken','turkey','beef','pork','lamb','steak','veal','bacon','ham','sausage','ground','meat','bison','goat','venison','duck','goose']
    if any(x in d for x in meat): return 'Protein'
    fish = ['salmon','tuna','cod','shrimp','fish','pollock','tilapia','mackerel','sardine','trout','halibut','crab','lobster','anchovy','herring','catfish','clam','mussel','oyster','scallop','squid','octopus','roe']
    if any(x in d for x in fish): return 'Seafood'
    dairy = ['egg','milk','cheese','yogurt','cream','butter','whey','casein','sour cream','kefir','ice cream','pudding','custard']
    if any(x in d for x in dairy): return 'Dairy'
    fruits = ['apple','banana','orange','berry','grape','melon','peach','pear','avocado','lemon','lime','plum','kiwi','mango','pineapple','raisin','date','fig','coconut','papaya','guava','cherry','apricot','nectarine','tangerine','grapefruit','cranberry','blueberry','raspberry','strawberry','blackberry','watermelon','honeydew']
    if any(x in d for x in fruits): return 'Fruits'
    veg = ['broccoli','spinach','kale','lettuce','carrot','onion','garlic','pepper','potato','tomato','cucumber','celery','cabbage','cauliflower','mushroom','bean','pea','corn','squash','asparagus','zucchini','radish','beet','turnip','parsnip','artichoke','eggplant','okra','chard','collard','arugula','endive','fennel','leek','shallot','jicama','watercress','seaweed','sea vegetable']
    if any(x in d for x in veg): return 'Vegetables'
    grain = ['rice','pasta','bread','oat','cereal','flour','grain','wheat','quinoa','barley','rye','couscous','noodle','tortilla','bagel','muffin','pancake','waffle','cornmeal','bran','farro','spelt','millet','sorghum','teff','amaranth','buckwheat']
    if any(x in d for x in grain): return 'Grains'
    nuts = ['almond','walnut','peanut','cashew','nut','seed','flax','chia','pecan','pistachio','macadamia','hazelnut','sesame','sunflower','pumpkin','hemp','pine nut','chestnut','coconut']
    if any(x in d for x in nuts): return 'Nuts & Seeds'
    if 'oil' in d: return 'Fats & Oils'
    beans_legumes = ['tofu','tempeh','seitan','lentil','chickpea','hummus','edamame','miso','soy']
    if any(x in d for x in beans_legumes): return 'Vegetables'
    bev = ['water','coffee','tea','juice','soda','beverage','smoothie','shake','sports drink','energy drink','cola']
    if any(x in d for x in bev): return 'Beverages'
    if 'soup' in d or 'sauce' in d or 'dressing' in d or 'mayo' in d or 'ketchup' in d or 'mustard' in d or 'vinegar' in d or 'salsa' in d or 'hummus' in d or 'dip' in d:
        return 'Condiments'
    if 'protein' in d or 'bar' in d or 'powder' in d:
        return 'Supplements'
    return 'Other'

queries = [
    ('chicken', 'Protein'), ('beef', 'Protein'), ('pork', 'Protein'),
    ('turkey', 'Protein'), ('lamb', 'Protein'), ('bacon', 'Protein'),
    ('ham', 'Protein'), ('sausage', 'Protein'),
    ('salmon', 'Seafood'), ('tuna', 'Seafood'), ('cod', 'Seafood'),
    ('shrimp', 'Seafood'), ('tilapia', 'Seafood'),
    ('egg', 'Dairy'), ('milk', 'Dairy'), ('cheese', 'Dairy'),
    ('yogurt', 'Dairy'), ('cream', 'Dairy'), ('butter', 'Dairy'),
    ('apple', 'Fruits'), ('banana', 'Fruits'), ('orange', 'Fruits'),
    ('berry', 'Fruits'), ('grape', 'Fruits'), ('melon', 'Fruits'),
    ('avocado', 'Fruits'), ('lemon', 'Fruits'),
    ('broccoli', 'Vegetables'), ('spinach', 'Vegetables'),
    ('kale', 'Vegetables'), ('lettuce', 'Vegetables'),
    ('carrot', 'Vegetables'), ('onion', 'Vegetables'),
    ('potato', 'Vegetables'), ('tomato', 'Vegetables'),
    ('cucumber', 'Vegetables'), ('cabbage', 'Vegetables'),
    ('mushroom', 'Vegetables'), ('corn', 'Vegetables'),
    ('pea', 'Vegetables'), ('bean', 'Vegetables'),
    ('rice', 'Grains'), ('pasta', 'Grains'), ('bread', 'Grains'),
    ('oat', 'Grains'), ('quinoa', 'Grains'),
    ('almond', 'Nuts & Seeds'), ('walnut', 'Nuts & Seeds'),
    ('peanut', 'Nuts & Seeds'), ('cashew', 'Nuts & Seeds'),
    ('flax', 'Nuts & Seeds'), ('chia', 'Nuts & Seeds'),
    ('olive oil', 'Fats & Oils'), ('coconut oil', 'Fats & Oils'),
    ('coffee', 'Beverages'), ('tea', 'Beverages'),
    ('tofu', 'Vegetables'), ('lentil', 'Vegetables'),
]

all_foods = []
seen_names = set()

limit_per_query = 50
for query, default_cat in queries:
    try:
        r = requests.get(f'{BASE}/foods/search', params={
            'query': query, 'dataType': 'Foundation',
            'pageSize': limit_per_query, 'api_key': API_KEY
        }, timeout=15)
        if not r.ok:
            print(f"Search '{query}': {r.status_code}", flush=True)
            continue
        data = r.json()
        foods = data.get('foods', [])
        if not foods:
            # Try SR Legacy if Foundation returns nothing
            r2 = requests.get(f'{BASE}/foods/search', params={
                'query': query, 'dataType': 'SR Legacy',
                'pageSize': limit_per_query, 'api_key': API_KEY
            }, timeout=15)
            if r2.ok:
                foods = r2.json().get('foods', [])
        for f in foods:
            desc = f.get('description', '')
            if desc.lower() in seen_names:
                continue
            seen_names.add(desc.lower())
            nutrients = {n.get('nutrientName',''): n for n in f.get('foodNutrients', [])}
            def get_nut(name):
                n = nutrients.get(name)
                return round(n.get('value'), 1) if n and n.get('value') is not None else None
            entry = {
                'name': desc,
                'source': f.get('dataType', '').lower().replace(' ','_'),
                'fdc_id': f.get('fdcId'),
                'category': categorize_food(desc),
                'serving_size': '100g',
            }
            for k, v in [('kcal_100g', get_nut('Energy')),
                         ('protein_100g', get_nut('Protein')),
                         ('fat_100g', get_nut('Total lipid (fat)')),
                         ('carbs_100g', get_nut('Carbohydrate, by difference')),
                         ('fiber_100g', get_nut('Fiber, total dietary')),
                         ('sugar_100g', get_nut('Sugars, total including NLEA')),
                         ('sodium_mg_100g', get_nut('Sodium, Na'))]:
                if v is not None:
                    entry[k] = v
            all_foods.append(entry)
        print(f"'{query}': {len(foods)} foods ({len(all_foods)} total)", flush=True)
        time.sleep(0.3)  # avoid rate limiting
    except Exception as e:
        print(f"Error '{query}': {e}", flush=True)

print(f"\nTotal unique foods: {len(all_foods)}", flush=True)
cats = {}
for f in all_foods:
    cats[f.get('category','Other')] = cats.get(f.get('category','Other'), 0) + 1
for c, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}", flush=True)

# Save
with open('knowledge/usda_foods.json', 'w', encoding='utf-8') as f:
    json.dump(all_foods, f, indent=2, ensure_ascii=False)
print("Saved to knowledge/usda_foods.json", flush=True)
