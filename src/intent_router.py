"""
Two-layer Intent Router for FitZone.

Layer 1 ? Topic scope check: Is this query about fitness/nutrition at all?
Layer 2 ? Domain routing: Classify into exercise_lookup, nutrition_lookup,
          calculation, or general_fitness and route to the correct retriever.

Uses keyword heuristics first, LLM classification as fallback (low temp, binary).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from src.config import GROQ_FAST_MODEL, GROQ_API_KEY

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

Domain = Literal[
    "exercise_lookup",
    "nutrition_lookup",
    "calculation",
    "general_fitness",
    "out_of_scope",
]


@dataclass
class RouteResult:
    """Result of intent routing."""
    domain: Domain
    confidence: float  # 0.0 to 1.0
    source: str  # "heuristic" or "llm"


# Keyword sets for domain routing
EXERCISE_KEYWORDS = frozenset({
    "exercise", "exercises", "workout", "lift", "lifting", "squat", "deadlift",
    "bench", "press", "row", "curl", "extension", "dip", "pullup", "pull-up",
    "pushup", "push-up", "lunge", "leg", "shoulder", "back", "chest", "bicep",
    "tricep", "forearm", "calves", "glute", "hamstring", "quad", "quadricep",
    "abs", "core", "cardio", "run", "running", "swim", "cycling", "machine",
    "dumbbell", "barbell", "cable", "kettlebell", "smith", "rack", "spotter",
    "form", "technique", "rep", "reps", "set", "sets", "routine", "split",
    "program", "volume", "intensity", "frequency", "muscle",
    "hypertrophy", "strength", "power", "olympic", "clean", "jerk", "snatch",
    "romanian", "rdl", "ohp", "hip", "thrust", "calf", "raise", "fly", "flies",
    "lat", "pulldown", "shrug", "crunch", "plank", "muscle-up", "dip",
    "benchpress", "squat", "deadlift", "overhead", "military", "front", "back",
    # More exercises
    "leg press", "legpress", "leg extension", "leg curl", "hamstring curl",
    "calf raise", "lat pulldown", "cable crossover", "face pull", "reverse fly",
    "lateral raise", "front raise", "upright row", "bent over row", "seated row",
    "t-bar row", "tbar row", "landmine", "trap bar", "hex bar", "ez bar", "swiss bar",
    "cambered bar", "safety bar", "ssb", "trap bar deadlift", "hack squat",
    "belt squat", "goblet squat", "bulgarian split squat", "pistol squat",
    "box squat", "pause squat", "front squat", "zercher squat",
    "romanian deadlift", "sumo deadlift", "conventional deadlift", "deficit deadlift",
    "block pull", "rack pull", "good morning", "hyperextension", "back extension",
    "reverse hyper", "glute bridge", "hip thrust", "hip bridge", "donkey kick",
    "fire hydrant", "clamshell", "abduction", "adduction", "leg abduction", "leg adduction",
    # Upper body specific
    "skull crusher", "tricep pushdown", "tricep extension", "overhead extension",
    "tricep kickback", "JM press", "close grip bench", "spoto press", "incline press",
    "decline press", "floor press", "pin press", "board press", "slingshot",
    "lateral raise", "rear delt", "anterior delt", "side raise", "shoulder press",
    "arnold press", "landmine press", "push press", "strict press", "seated press",
    "dumbbell press", "machine press", "pec deck", "chest fly", "cable fly",
    "dumbbell fly", "incline fly", "decline fly",
    # Lats & back
    "chinup", "chin-up", "neutral grip pullup", "wide grip pulldown", "close grip pulldown",
    "v-bar pulldown", "straight arm pulldown", "pullover", "db pullover",
    "cable pullover", "seated cable row", "chest supported row", "meadows row",
    "pendlay row", "barbell row", "dumbbell row", "kroc row", "single arm row",
    "inverted row", "ring row", "bodyweight row", "australian pullup",
    # Arms
    "barbell curl", "dumbbell curl", "hammer curl", "preacher curl", "concentration curl",
    "incline curl", "bayesian curl", "cable curl", "ez bar curl", "spider curl",
    "reverse curl", "wrist curl", "farmer carry", "suitcase carry", "waiter carry",
    "zottman curl", "21s", "drag curl",
    # Core
    "russian twist", "hanging leg raise", "lying leg raise", "v-up", "jackknife",
    "ab wheel", "rollout", "ab crunch", "cable crunch", "machine crunch",
    "pallof press", "dead bug", "hollow hold", "arch hold", "side plank",
    "bird dog", "mountain climber", "spiderman plank", "bear crawl",
    # Training styles & methodologies
    "hiit", "hitt", "liss", "circuit", "superset", "supersets", "dropset", "dropsets",
    "pyramid", "reverse pyramid", "cluster", "rest pause", "rest-pause", "myo rep",
    "myorep", "myo-rep", "isometric", "eccentric", "negative", "negatives",
    "concentric", "tempo", "time under tension", "tut",
    "amrap", "emom", "tabata", "interval", "intervals", "fartlek",
    "rpe", "rir", "rm", "repetition maximum", "one rep max", "1rm",
    "progressive overload", "double progression", "linear progression",
    "periodization", "dup", "undulating", "block periodization",
    "conjugate", "westside", "5/3/1", "531", "starting strength",
    "stronglifts", "ppl", "phul", "phat", "upper lower", "bro split",
    "push pull", "pull push", "legs push pull", "full body", "whole body",
    # Cardio & conditioning
    "treadmill", "elliptical", "stairmaster", "stepmill", "stationary bike",
    "spin bike", "assault bike", "airdyne", "rower", "rowing machine",
    "ski erg", "versa climber", "jacob ladder", "stepmill", "incline walk",
    "sprint", "jog", "jogging", "brisk walk", "power walk", "hike", "hiking",
    "bike", "cycling", "spinning", "swim", "swimming", "lap", "laps",
    # Yoga & flexibility
    "yoga", "pilates", "barre", "vinyasa", "hatha", "ashtanga", "bikram",
    "hot yoga", "yin", "restorative", "asana", "flows",
    # Equipment
    "resistance band", "resistance bands", "loop band", "mini band", "slam ball",
    "wall ball", "medicine ball", "bosu ball", "stability ball", "swiss ball",
    "yoga mat", "exercise mat", "battle rope", "battling rope", "jump rope",
    "skipping rope", "speed rope", "plyo box", "plyometric box", "box jump",
    "parallettes", "dip bar", "dip bars", "pullup bar", "chinup bar",
    "gloves", "lifting gloves", "straps", "wrist straps", "lifting belt",
    "knee sleeves", "elbow sleeves", "wrist wraps", "chalk", "liquid chalk",
    "lifting shoes", "deadlift shoes", "squat shoes", "olympic shoes",
    "crossfit shoes", "training shoes", "sneakers", "gym bag",
    # Gym areas & facilities
    "free weight", "free weights", "dumbbell rack", "barbell rack",
    "squat rack", "power rack", "half rack", "full rack",
    "locker room", "changing room", "shower", "sauna", "steam room",
    "pool", "jacuzzi", "hot tub", "cold plunge", "ice bath",
    "gym floor", "lifting platform", "deadlift platform", "competition platform",
    "cardio area", "cardio deck", "functional area", "functional training",
    "stretching area", "yoga studio", "group fitness room", "cycle studio",
    "crossfit box", "home gym", "garage gym", "basement gym", "hotel gym",
    "outdoor gym", "outdoor workout", "park workout", "bodyweight",
    # Sports & activities
    "basketball", "football", "soccer", "rugby", "tennis", "badminton",
    "volleyball", "handball", "hockey", "baseball", "softball", "golf",
    "boxing", "kickboxing", "muay thai", "bjj", "jiu jitsu", "judo",
    "karate", "taekwondo", "mma", "mixed martial arts", "wrestling",
    "calisthenics", "gymnastics", "dance", "zumba", "aerobics", "step aerobics",
    "bodypump", "bodycombat", "bodyattack", "bodybalance", "les mills",
    "marathon", "half marathon", "triathlon", "ironman", "sprint tri",
    "obstacle course", "spartan", "tough mudder", "warrior dash", "mud run",
    "parkour", "free running", "rock climbing", "bouldering", "climbing",
    "swimming", "open water", "lap swimming", "pool workout",
    "skating", "ice skating", "rollerblading", "skiing", "snowboarding",
    "surfing", "paddleboarding", "sup", "kayaking", "rowing", "canoeing",
    # Movement patterns & techniques
    "hinge", "hinging", "squat pattern", "hip hinge", "push", "pull",
    "loaded carry", "locomotion", "groundwork", "primal movement",
    "overhead", "overhead press", "vertical push", "vertical pull",
    "horizontal push", "horizontal pull",
})

NUTRITION_KEYWORDS = frozenset({
    "calorie", "calories", "kcal", "macro", "macros", "protein", "carb",
    "carbs", "fat", "fats", "nutrition", "nutrients", "food", "foods", "eat",
    "eating", "meal", "meals", "snack", "snacks", "breakfast", "lunch",
    "dinner", "diet", "ingredient", "serving", "gram", "grams", "ounce",
    "chicken", "rice", "salmon", "egg", "eggs", "oatmeal", "pasta", "bread",
    "milk", "cheese", "beef", "pork", "fish", "yogurt", "apple", "banana",
    "vegetable", "fruit", "smoothie", "shake", "whey", "supplement",
    "vitamin", "mineral", "nutrient", "fiber", "sugar", "sodium",
    "avocado", "almonds", "oats", "quinoa", "broccoli",
    # More proteins
    "turkey", "bacon", "ham", "venison", "lamb", "bison", "veal", "duck",
    "chicken breast", "chicken thigh", "ground beef", "steak", "ribeye",
    "sirloin", "filet", "tenderloin", "flank", "skirt", "brisket",
    "tuna", "tilapia", "cod", "halibut", "mahi", "mahi", "trout", "sardines",
    "mackerel", "herring", "anchovies", "shrimp", "prawns", "crab", "lobster",
    "scallop", "mussel", "clam", "oyster", "calamari", "squid",
    "tofu", "tempeh", "seitan", "edamame", "soy", "bean", "beans",
    "lentil", "lentils", "chickpea", "chickpeas", "garbanzo", "black bean",
    "kidney bean", "pinto bean", "navy bean", "lima bean", "cannellini",
    "peanut", "peanuts", "cashew", "cashews", "walnut", "walnuts",
    "pecan", "pecans", "pistachio", "macadamia", "almond", "chestnut",
    "brazil nut", "hazelnut", "pine nut", "seed", "seeds", "chia", "flax",
    "hemp", "hempseed", "sunflower seed", "pumpkin seed", "sesame", "poppy",
    "quinoa", "amaranth", "buckwheat", "spelt", "farro", "barley", "millet",
    "couscous", "semolina", "polenta", "grits", "cornmeal",
    # Vegetables
    "spinach", "kale", "lettuce", "romaine", "arugula", "watercress",
    "cabbage", "sauerkraut", "kimchi", "bok choy", "collard", "chard",
    "mustard green", "beetroot", "beet", "radish", "turnip", "parsnip",
    "carrot", "celery", "celeriac", "tomato", "tomatoes", "cucumber",
    "zucchini", "yellow squash", "butternut", "acorn squash", "pumpkin",
    "bell pepper", "pepper", "peppers", "chili", "jalapeno", "habanero",
    "onion", "onions", "shallot", "leek", "scallion", "green onion", "chive",
    "garlic", "ginger", "turmeric", "horseradish", "wasabi",
    "mushroom", "mushrooms", "portobello", "shiitake", "oyster mushroom",
    "broccoli", "cauliflower", "brussels sprout", "asparagus", "artichoke",
    "green bean", "snap pea", "snow pea", "pea", "peas", "sweet corn", "corn",
    "potato", "potatoes", "sweet potato", "yam", "fries", "wedges",
    "olive", "olives", "pickle", "pickles",
    # Fruits
    "strawberry", "strawberries", "blueberry", "blueberries", "raspberry",
    "raspberries", "blackberry", "blackberries", "cranberry", "cherry",
    "cherries", "grape", "grapes", "raisin", "raisins", "date", "dates",
    "fig", "figs", "prune", "prunes", "apricot", "nectarine", "peach",
    "plum", "plums", "mango", "pineapple", "papaya", "guava", "coconut",
    "watermelon", "cantaloupe", "honeydew", "melon", "orange", "oranges",
    "tangerine", "clementine", "grapefruit", "lemon", "lime", "kiwi",
    "dragon fruit", "lychee", "passion fruit", "persimmon", "pomegranate",
    "rhubarb", "plantain",
    # Dairy & alternatives
    "greek yogurt", "skyr", "cottage cheese", "ricotta", "mozzarella",
    "parmesan", "cheddar", "swiss", "gouda", "provolone", "pepper jack",
    "feta", "goat cheese", "cream cheese", "sour cream", "cream", "half and half",
    "butter", "ghee", "margarine", "plant butter",
    "almond milk", "soy milk", "oat milk", "coconut milk", "rice milk",
    "hemp milk", "cashew milk", "protein milk",
    # Grains & starches
    "white rice", "brown rice", "jasmine rice", "basmati rice", "wild rice",
    "sushi rice", "risotto", "sticky rice", "whole wheat", "white bread",
    "whole grain", "sourdough", "rye", "pumpernickel", "tortilla", "wrap",
    "pita", "naan", "bagel", "english muffin", "croissant", "muffin",
    "pancake", "waffle", "french toast", "crepe",
    "pasta", "spaghetti", "linguine", "fettuccine", "penne", "rigatoni",
    "mac and cheese", "lasagna", "ravioli", "tortellini", "gnocchi",
    "ramen", "udon", "soba", "rice noodle", "vermicelli",
    "oatmeal", "porridge", "granola", "muesli", "cereal", "cheerios",
    "wheaties", "special k", "fiber one", "bran",
    # Condiments & sauces
    "ketchup", "mustard", "mayonnaise", "hot sauce", "sriracha",
    "soy sauce", "teriyaki", "bbq sauce", "barbecue", "ranch",
    "italian dressing", "vinaigrette", "balsamic", "olive oil",
    "coconut oil", "avocado oil", "canola oil", "vegetable oil",
    "sesame oil", "peanut oil", "truffle oil", "MCT oil",
    "salt", "pepper", "black pepper", "seasoning", "spice", "spices",
    "cinnamon", "paprika", "cumin", "oregano", "thyme", "rosemary",
    "basil", "parsley", "cilantro", "mint", "dill", "bay leaf",
    "curry", "turmeric", "coriander", "cardamom", "nutmeg", "clove",
    "vanilla", "cocoa", "chocolate", "dark chocolate", "cacao",
    # Cooking methods
    "cook", "cooking", "bake", "baked", "baking", "grill", "grilled",
    "broil", "broiled", "roast", "roasted", "roasting", "saute", "sauteed",
    "steam", "steamed", "steaming", "boil", "boiled", "poach", "poached",
    "fry", "fried", "frying", "air fry", "air fried", "airfryer",
    "slow cook", "slow cooker", "crockpot", "instant pot", "pressure cook",
    "smoke", "smoked", "smoking", "sear", "seared", "braise", "braised",
    "stir fry", "stir-fry", "blanch", "blanched",
    "meal prep", "mealprep", "meal preparation", "batch cook",
    # Dietary patterns
    "keto", "ketogenic", "paleo", "whole30", "vegan", "vegetarian",
    "lacto vegetarian", "ovo vegetarian", "lacto-ovo", "pescatarian",
    "flexitarian", "omnivore", "carnivore", "mediterranean",
    "intermittent fasting", "if", "time restricted feeding", "trf",
    "feeding window", "fasting", "fasted", "fast", "fasts",
    "16/8", "18/6", "20/4", "omad", "alternate day fasting", "adf",
    "carb cycling", "calorie cycling", "refeed", "refeeds",
    "volume eating", "nutrient timing", "peri-workout", "pre-workout",
    "post-workout", "intra-workout", "around workout",
    # Drinks
    "water", "drink", "drinks", "drinking", "hydration", "hydrate",
    "coffee", "espresso", "latte", "cappuccino", "americano", "mocha",
    "tea", "black tea", "green tea", "matcha", "oolong", "herbal tea",
    "chamomile", "peppermint", "ginger tea", "hibiscus",
    "juice", "orange juice", "apple juice", "cranberry juice", "grape juice",
    "soda", "diet soda", "coke", "pepsi", "sparkling water", "seltzer",
    "club soda", "tonic water", "gatorade", "powerade", "sports drink",
    "electrolyte", "electrolytes", "coconut water",
    "protein shake", "protein shake", "protein powder",
    "almond milk", "soy milk", "oat milk", "coconut milk",
    # Supplements (non-medical)
    "creatine", "creatine monohydrate", "creatine hcl",
    "beta alanine", "beta-alanine", "citrulline", "citrulline malate",
    "arginine", "l-arginine", "glutamine", "l-glutamine",
    "taurine", "carnitine", "l-carnitine", "acetyl l-carnitine",
    "bcaa", "bcaas", "eaa", "eaas", "leucine", "isoleucine", "valine",
    "preworkout", "pre-workout", "pre workout", "pump supplement",
    "postworkout", "post-workout", "post workout",
    "intraworkout", "intra-workout", "intra workout",
    "multivitamin", "multi vitamin", "daily vitamin",
    "omega 3", "omega-3", "omega3", "fish oil", "cod liver oil",
    "probiotic", "probiotics", "digestive enzyme", "digestive enzymes",
    "greens powder", "super greens", "spirulina", "chlorella", "wheatgrass",
    "collagen", "collagen peptide", "gelatin",
    "mass gainer", "weight gainer", "gainer", "carbo gain",
    "fat burner", "thermogenic", "cla", "conjugated linoleic acid",
    "zma", "zinc magnesium",
    # Tools & tracking
    "food scale", "kitchen scale", "measuring cup", "measuring spoon",
    "meal prep container", "lunch box", "cooler", "shaker bottle", "shaker",
    "blender", "nutribullet", "vitamix", "ninja",
    "myfitnesspal", "mfp", "cronometer", "macrofactor", "carb manager",
    "lose it", "fat secret", "calorie tracker", "macro tracker",
    # Recipe keyword — critical for "give me a recipe"
    "recipe", "recipes",
})

CALCULATION_KEYWORDS = frozenset({
    "bmr", "tdee", "bmi", "1rm", "bodyfat", "calculate", "calculation",
    "formula", "compute", "estimate", "karvonen", "acwr", "irv",
    "progression", "recommend", "target", "zone", "percentage", "ratio",
})

FITNESS_KEYWORDS = frozenset({
    # Core fitness
    "gym", "fitness", "training", "workout", "exercise", "health",
    "wellness", "recovery", "sleep", "warmup", "cooldown", "stretch",
    "mobility", "flexibility", "injury", "pain", "rehab", "posture",
    "motivation", "goal", "habit", "consistency", "mindset",
    "heart", "cardiac", "condition",
    # Body parts
    "head", "neck", "shoulder", "shoulders", "elbow", "elbows",
    "wrist", "wrists", "hand", "hands", "finger", "fingers", "thumb",
    "spine", "rib", "ribs", "abdomen", "hip", "hips", "pelvis",
    "glute", "glutes", "knee", "knees", "leg", "legs", "thigh", "thighs",
    "shin", "shins", "calf", "calves", "ankle", "ankles", "foot", "feet",
    "toe", "toes", "joint", "joints", "bone", "bones", "muscle", "muscles",
    "tendon", "tendons", "ligament", "ligaments", "nerve", "nerves",
    "disc", "discs", "vertebra", "vertebrae", "cartilage", "meniscus",
    "rotator", "labrum", "spine", "spinal", "cervical", "thoracic", "lumbar",
    "sacrum", "coccyx", "tailbone", "scapula", "scapulae", "clavicle",
    "sternum", "femur", "tibia", "fibula", "humerus", "radius", "ulna",
    "patella", "mandible", "cranium", "skull",
    # Common injuries
    "acl", "mcl", "lcl", "pcl", "concussion", "tbi", "whiplash",
    "sprain", "strain", "fracture", "break", "dislocation", "subluxation",
    "tear", "rupture", "pull", "torn", "broken", "twisted", "rolled",
    "contusion", "bruise", "hematoma", "laceration", "cut", "wound",
    "scar", "burn", "blister", "callus", "shinsplints", "shin splints",
    "stress fracture", "hairline fracture", "compression fracture",
    "avulsion", "bone bruise", "bone spur", "cyst", "ganglion",
    # Symptoms & sensations
    "ache", "aching", "sore", "soreness", "stiffness", "tight", "tightness",
    "swelling", "swollen", "inflammation", "inflamed", "numb", "numbness",
    "tingling", "burning", "cramp", "cramps", "cramping", "spasm", "spasms",
    "fatigue", "dizzy", "dizziness", "nausea", "headache", "migraine",
    "fever", "chills", "weak", "weakness", "tender", "tenderness",
    "pulsating", "throbbing", "sharp", "stabbing", "radiating", "referred",
    "aching", "gnawing", "pressure", "heaviness", "lightheaded",
    "lightheadedness", "faint", "fainting", "syncope", "seizure",
    "tremor", "tremors", "shaking", "twitch", "twitching", "fasciculation",
    "vertigo", "bloating", "constipation", "diarrhea", "indigestion",
    "heartburn", "reflux", "gas", "flatulence", "nausea", "vomiting",
    # Diseases & chronic conditions
    "diabetes", "type1", "type2", "prediabetes", "asthma", "hypertension",
    "hypotension", "arthritis", "osteoarthritis", "osteoarthrosis",
    "osteoporosis", "osteopenia", "scoliosis", "kyphosis", "lordosis",
    "fibromyalgia", "chronic fatigue", "myalgic", "cfs", "ibs", "ibd",
    "crohns", "crohn", "colitis", "ulcerative", "gerd", "acid reflux",
    "thyroid", "hyperthyroidism", "hypothyroidism", "hashimoto", "graves",
    "anemia", "sickle cell", "thalassemia", "hemophilia", "hemochromatosis",
    "epilepsy", "seizure disorder", "multiple sclerosis", "ms", "als",
    "parkinsons", "parkinson", "alzheimers", "alzheimer", "dementia",
    "cancer", "tumor", "polyp", "hernia", "hiatal", "inguinal", "umbilical",
    "sciatica", "sciatic", "stenosis", "spondylosis", "spondylitis",
    "spondylolisthesis", "spondylolysis", "bursitis", "tendinitis",
    "tendonitis", "tendinopathy", "tendinosis", "epicondylitis",
    "tennis elbow", "golfers elbow", "golfer elbow", "carpal tunnel",
    "plantar fasciitis", "fasciitis", "shin splint", "shinsplints",
    "autoimmune", "lupus", "sle", "rheumatoid", "ra", "psoriatic",
    "ankylosing", "spondyloarthritis", "gout", "pseudogout", "lyme",
    "long covid", "post covid", "pots", "eds", "hypermobility",
    "ehlers danlos", "mcas", "mast cell",
    "sinusitis", "bronchitis", "pneumonia", "copd", "emphysema",
    "sleep apnea", "osa", "insomnia", "narcolepsy", "restless leg",
    "rls", "periodic limb", "adhd", "add", "anxiety", "depression",
    "bipolar", "ptsd", "ocd", "eating disorder", "anorexia", "anorexic",
    "bulimia", "bulimic", "orthorexia", "body dysmorphia", "bd",
    "dysmorphia", "bigorexia", "muscle dysmorphia",
    "high cholesterol", "hyperlipidemia", "high blood pressure",
    "low blood pressure", "irregular heartbeat", "arrhythmia",
    "afib", "atrial fibrillation", "tachycardia", "bradycardia",
    "palpitations", "heart palpitations", "murmur", "heart murmur",
    "mitral valve", "aortic", "cardiomyopathy", "heart failure",
    "chf", "congestive heart", "coronary artery", "cad", "pad",
    "peripheral artery", "dvt", "deep vein", "pulmonary embolism",
    "stroke", "tia", "mini stroke", "aneurysm", "angiogram", "stent",
    "bypass", "pacemaker",
    # Mental health
    "stress", "burnout", "overwhelmed", "mental health", "wellbeing",
    "well-being", "therapy", "counseling", "counselling", "psychologist",
    "psychiatrist", "therapist", "counselor", "counsellor",
    "mood", "anxiety", "depression", "panic", "panic attack",
    # Surgeries & procedures
    "surgery", "surgical", "operation", "replacement", "reconstruction",
    "repair", "transplant", "implant", "arthroscopy", "arthroscopic",
    "endoscopy", "endoscopic", "laparoscopy", "laparoscopic",
    "injection", "shot", "cortisone", "corticosteroid", "steroid injection",
    "anti-inflammatory", "antiinflammatory", "nsaid", "ibuprofen",
    "aspirin", "acetaminophen", "tylenol", "advil", "aleve", "naproxen",
    "prescription", "medication", "medicine", "pill", "tablet", "capsule",
    "dose", "dosage", "prescribed", "rx", "over the counter", "otc",
    # Healthcare professionals
    "doctor", "physician", "surgeon", "specialist", "orthopedist",
    "orthopedic", "orthopaedic", "ortho", "cardiologist", "neurologist",
    "rheumatologist", "endocrinologist", "gastroenterologist",
    "dermatologist", "podiatrist", "physiatrist", "physical therapist",
    "pt", "physio", "physiotherapist", "chiropractor", "chiro",
    "acupuncturist", "massage therapist", "osteopath",
    "athletic trainer", "strength coach", "sports medicine",
    # Lifestyle & daily routine
    "routine", "daily", "morning", "evening", "schedule", "habit", "discipline",
    "commitment", "dedication", "lifestyle", "behavior change", "habit building",
    "accountability", "self improvement", "personal development",
    "transformation", "journey", "fitness journey", "path", "fitness path",
    # Wellness & recovery (non-medical)
    "meditation", "mindfulness", "breathing", "breathwork", "deep breath",
    "box breathing", "diaphragmatic", "relaxation", "calm", "de-stress",
    "self care", "self-care", "balance", "work life balance",
    "rest day", "rest days", "active recovery", "deload", "deloading",
    "unload", "recovery day", "off day", "rest period",
    # Body composition & physique
    "physique", "aesthetics", "shredded", "ripped", "jacked", "swole",
    "yoked", "hench", "buff", "cut", "ripped", "vascular", "veiny",
    "toned", "tone", "definition", "lean", "lean mass", "fat loss",
    "muscle gain", "muscle growth", "mass", "size", "bulk", "bulking",
    "lean bulk", "clean bulk", "dirty bulk", "maingaining",
    "mini cut", "mini bulk", "body recomposition", "recomp", "recomposition",
    "cutting", "bulking phase", "cutting phase", "off season", "prep",
    # Progress & metrics
    "progress", "progress pic", "transformation", "before after", "before and after",
    "milestone", "personal record", "personal best", "pr", "pb",
    "achievement", "accomplishment", "result", "outcome", "improvement",
    "gain", "gains", "gainz", "noob gain", "newbie gain", "beginner gain",
    "strength gain", "muscle gain", "size gain",
    "plateau", "stalling", "stuck", "breakthrough", "stagnation",
    # Measurements & tracking
    "weight", "weigh", "weighing", "scale", "scale weight",
    "tape measure", "measuring tape", "measuring", "measurements",
    "waist measurement", "hip measurement", "chest measurement",
    "arm measurement", "thigh measurement", "neck measurement", "circumference",
    "body fat", "bodyfat", "bf", "bf%", "body fat percentage",
    "caliper", "calipers", "skinfold", "skin fold",
    "dexa", "dexa scan", "bod pod", "hydrostatic weighing", "inbody",
    "smart scale", "withings", "renpho", "fitindex", "eufy",
    "progress tracker", "fitness tracker", "tracking", "log", "logbook",
    "journal", "training log", "workout log", "food log", "food diary",
    # Age & experience
    "beginner", "beginners", "novice", "intermediate", "advanced", "elite",
    "newbie", "newb", "new", "starting", "starter", "fresh", "first time",
    "new to fitness", "just started", "getting started", "starting out",
    "lifter", "experienced", "seasoned", "veteran",
    # Life stages
    "pregnancy", "pregnant", "postpartum", "postnatal", "prenatal",
    "antenatal", "mother", "mom", "mum", "father", "dad", "parent",
    "menopause", "postmenopause", "perimenopause", "andropause",
    "aging", "older", "elderly", "senior", "age", "youth",
    "teenager", "adolescent", "teen", "kids", "children", "child",
    # Fitness professionals & coaching
    "trainer", "personal trainer", "pt", "coach", "strength coach",
    "gym instructor", "fitness instructor", "group instructor",
    "class instructor", "yoga teacher", "yoga instructor",
    "pilates instructor", "spin instructor", "crossfit coach",
    "online coach", "virtual coach", "remote coach", "coaching",
    "program design", "programming", "custom program", "custom plan",
    "1 on 1", "one on one", "private training", "personal training",
    "session", "training session", "pt session",
    # Fitness community & social
    "gym buddy", "workout buddy", "training partner", "lifting partner",
    "accountability partner", "fitness community", "fitness family",
    "gym community", "fitfam", "gymfam",
    "instagram", "youtube", "tiktok", "fitness influencer", "fitness model",
    "online fitness", "fitness app", "app",  # "app" needed so "tracking app" etc isn't OOS
    # Fitness events
    "competition", "contest", "show", "bodybuilding show", "powerlifting meet",
    "weightlifting meet", "strongman competition", "strongman show",
    "crossfit open", "crossfit games", "marathon", "race", "charity run",
    "fun run", "parkrun", "triathlon", "sprint", "meet", "tournament",
    "championship", "league", "challenge", "fitness challenge",
    "transformation challenge", "bet", "wager", "competition prep",
    # Environment & logistics
    "home gym", "garage gym", "basement gym", "hotel gym", "apartment gym",
    "outdoor", "outdoor workout", "park", "park workout", "beach workout",
    "travel", "traveling", "travelling", "vacation", "holiday",
    "business trip", "work trip", "on the road", "hotel room",
    "limited equipment", "no equipment", "bodyweight only",
    "weather", "cold weather", "hot weather", "rain", "snow", "heat",
    "humidity", "altitude", "indoor", "outdoor", "sun", "summer", "winter",
    "time crunch", "busy", "short workout", "quick workout", "express workout",
    "time efficient", "minimalist", "minimal equipment",
    # Tracking & tech (non-medical)
    "app", "fitness app", "tracking app", "workout app", "nutrition app",
    "calorie counter", "calorie tracker", "macro tracker",
    "fitbit", "garmin", "apple watch", "whoop", "oura", "oura ring",
    "polar", "suunto", "coros", "amazfit", "mi band", "xiaomi",
    "smartwatch", "smart watch", "fitness tracker", "activity tracker",
    "wearable", "wearables", "hr monitor", "heart rate monitor", "chest strap",
    "myfitnesspal", "mfp", "cronometer", "macrofactor", "carb manager",
    "carbon diet", "strong", "hevy", "fitnotes", "progression",
    "strava", "trainingpeaks", "nike run club", "nikerun",
    "nike training club", "freeletics", "fitbod", "jefit", "bodybuilding",
    # Gym culture & slang
    "gym rat", "gym bro", "gym girl", "gym life", "gym lifestyle",
    "gains", "gainz", "grind", "grinding", "hustle", "dedication",
    "no pain no gain", "mind muscle connection", "mmc",
    "pump", "muscle pump", "skin splitting", "full pump",
    "sore", "soreness", "doms", "delayed onset",
    "cheat meal", "cheat day", "refeed", "treat meal",
    "leg day", "arm day", "chest day", "back day", "push day", "pull day",
    "rest day", "chest day", "shoulder day",
    # Activity levels
    "sedentary", "lightly active", "moderately active", "very active",
    "extremely active", "activity level", "neat",
    "desk job", "office job", "office worker", "desk bound",
    "standing desk", "walking pad", "treadmill desk",
    "active lifestyle", "active", "inactive",
    # Fitness concepts & physiology (non-medical)
    "sweat", "sweating", "energy", "endurance", "stamina",
    "conditioning", "work capacity", "workload",
    "speed", "agility", "quickness", "explosiveness", "power output",
    "balance", "coordination", "proprioception",
    "pump", "the pump", "muscle pump", "fullness",
    "mind muscle connection", "mmc", "mind-muscle",
    "tempo", "timing", "rhythm", "cadence",
    "breathing", "breathe", "exhale", "inhale", "valsalva",
    "form", "technique", "mechanics", "setup", "bracing",
    "grinding", "grinder", "fight", "push through",
    # Goals & motivation
    "goal", "goals", "target", "targets", "aim", "objective",
    "fitness goal", "weight goal", "strength goal", "aesthetic goal",
    "performance goal", "body goal", "physique goal",
    "motivation", "motivate", "motivated", "inspiring", "inspire",
    "inspiration", "drive", "determination", "willpower", "mindset",
    # General fitness adjacent words currently in OUT_OF_SCOPE that need rescue
    "travel", "weather", "app", "recipe",
    "delayed onset", "rhabdo", "rhabdomyolysis", "dehydration",
    "heat stroke", "heat exhaustion", "hypothermia", "hyperthermia",
    "bonk", "bonking", "hitting the wall", "stitch", "stitches",
    "side stitch", "side stitches", "chafing", "chafe", "blisters",
    "calluses", "corns", "ingrown", "black toenail", "runners knee",
    "jumpers knee", "patellar", "patellofemoral", "IT band", "itband",
    "ITBS", "piriformis", "hamstring strain", "groin pull", "groin strain",
    "hip flexor", "hip impingement", "fai", "snapping hip",
    # Rehab & recovery
    "physical therapy", "physiotherapy", "rehab", "rehabilitation",
    "occupational therapy", "ot", "speech therapy",
    "massage", "acupuncture", "dry needling", "cupping", "graston",
    "instrument assisted", "iak", "art", "active release",
    "foam rolling", "foam roller", "lacrosse ball", "massage gun",
    "theragun", "percussive", "vibration", "compression",
    "ice", "icing", "cryotherapy", "heat", "heating", "warm compress",
    "cold compress", "cold therapy", "contrast bath", "epsom salt",
    "elevation", "compression", "brace", "bracing", "splint", "sling",
    "crutches", "cane", "walker", "boot", "cast", "bandage", "wrap",
    "kinesio", "kt tape", "athletic tape", "taping",
    "rest", "active recovery", "deload", "deloading", "unload",
    "regression", "progression", "return to sport", "clearance",
    "cleared", "released", "graduated",
})

OUT_OF_SCOPE_KEYWORDS = frozenset({
    "python", "javascript", "code", "programming", "stock",
    "election", "politics", "movie", "sql", "kubernetes", "docker", "react",
    "homework", "essay", "poem", "story", "flight",
    "crypto", "bitcoin", "algebra", "calculus", "history", "coding",
    "software", "website", "database", "server", "deploy",
})

GREETING_KEYWORDS = frozenset({
    "hey", "hi", "hello", "sup", "yo", "morning", "evening", "afternoon",
    "thanks", "thank", "bye", "goodbye", "cheers", "appreciate", "coach",
    "bro", "dude", "man", "help",
    "yes", "yeah", "yep", "yup", "sure", "ok", "okay", "alright", "kk",
    "no", "nope", "nah", "maybe", "idk",
    "cool", "thx", "ty", "k", "nice", "great", "awesome", "perfect",
    "gotcha", "understood", "sweet", "deal", "fine",
})


class IntentRouter:
    """
    Two-layer intent router.
    
    Layer 1: Scope check (in-scope vs out-of-scope)
    Layer 2: Domain routing (exercise, nutrition, calculation, general)
    
    Uses keyword heuristics first, falls back to LLM for ambiguous queries.
    """

    def __init__(self, model: str = GROQ_FAST_MODEL) -> None:
        self._model = model
        self._llm = None

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(TOKEN_PATTERN.findall(text.lower()))

    # ------------------------------------------------------------------
    # Layer 1: Scope check
    # ------------------------------------------------------------------

    def _heuristic_scope(self, tokens: set[str]) -> str | None:
        """Quick heuristic scope classification."""
        if tokens & OUT_OF_SCOPE_KEYWORDS and not (tokens & (FITNESS_KEYWORDS | NUTRITION_KEYWORDS | EXERCISE_KEYWORDS)):
            return "OUT_OF_SCOPE"
        if tokens & (FITNESS_KEYWORDS | NUTRITION_KEYWORDS | EXERCISE_KEYWORDS | CALCULATION_KEYWORDS):
            return "IN_SCOPE"
        # Short greetings/pleasantries
        if len(tokens) < 3 and tokens & GREETING_KEYWORDS and not (tokens & OUT_OF_SCOPE_KEYWORDS):
            return "IN_SCOPE"
        # Longer queries with greeting mixed in
        if tokens & GREETING_KEYWORDS and not (tokens & OUT_OF_SCOPE_KEYWORDS):
            return "IN_SCOPE"
        return None

    def _llm_scope(self, query: str) -> bool:
        """LLM-based scope classification fallback."""
        try:
            from langchain_groq import ChatGroq
            from langchain_core.messages import HumanMessage, SystemMessage
            from src.config import INTENT_CLASSIFIER_PROMPT

            if self._llm is None:
                self._llm = ChatGroq(model=self._model, temperature=0.0)

            messages = [
                SystemMessage(content=INTENT_CLASSIFIER_PROMPT),
                HumanMessage(content=query),
            ]
            response = self._llm.invoke(messages)
            result = (response.content or "").strip().upper()
            return "IN_SCOPE" in result
        except Exception:
            # If LLM fails, default to in-scope (let the knowledge retriever handle it)
            return True

    def classify_scope(self, user_query: str) -> bool:
        """
        Layer 1: Returns True if in-scope, False if out-of-scope.
        """
        tokens = self._tokenize(user_query)
        heuristic = self._heuristic_scope(tokens)
        if heuristic == "OUT_OF_SCOPE":
            return False
        if heuristic == "IN_SCOPE":
            return True
        # Ambiguous ? use LLM
        return self._llm_scope(user_query)

    # ------------------------------------------------------------------
    # Layer 2: Domain routing
    # ------------------------------------------------------------------

    def _heuristic_domain(self, tokens: set[str], query_lower: str) -> Domain | None:
        """Heuristic domain classification."""
        # Check calculations first (specific keywords)
        calc_score = len(tokens & CALCULATION_KEYWORDS)
        if calc_score >= 1:
            # Verify it's actually a calculation request
            calc_phrases = ["calculate", "compute", "estimate", "how many", "how much", "what is my"]
            if any(phrase in query_lower for phrase in calc_phrases) or calc_score >= 2:
                return "calculation"

        exercise_score = len(tokens & EXERCISE_KEYWORDS)
        nutrition_score = len(tokens & NUTRITION_KEYWORDS)

        if exercise_score > nutrition_score and exercise_score >= 1:
            return "exercise_lookup"
        if nutrition_score > exercise_score and nutrition_score >= 1:
            return "nutrition_lookup"
        if exercise_score > 0:
            return "exercise_lookup"
        if nutrition_score > 0:
            return "nutrition_lookup"

        if tokens & FITNESS_KEYWORDS:
            return "general_fitness"

        return None

    def classify_domain(self, user_query: str) -> RouteResult:
        """
        Full two-layer routing.
        Returns RouteResult with domain, confidence, and source.
        """
        tokens = self._tokenize(user_query)
        query_lower = user_query.lower()

        # Layer 1: Scope check
        scope_heuristic = self._heuristic_scope(tokens)
        if scope_heuristic == "OUT_OF_SCOPE":
            return RouteResult(domain="out_of_scope", confidence=0.95, source="heuristic")

        # Layer 2: Domain routing
        domain = self._heuristic_domain(tokens, query_lower)
        if domain is not None:
            return RouteResult(domain=domain, confidence=0.85, source="heuristic")

        # If scope is ambiguous and domain is ambiguous, use LLM for scope
        if scope_heuristic is None:
            if not self._llm_scope(user_query):
                return RouteResult(domain="out_of_scope", confidence=0.7, source="llm")
            # In-scope but domain unclear ? general fitness
            return RouteResult(domain="general_fitness", confidence=0.6, source="llm")

        return RouteResult(domain="general_fitness", confidence=0.5, source="heuristic")


# Singleton
_router: IntentRouter | None = None


def get_intent_router() -> IntentRouter:
    """Get the singleton IntentRouter instance."""
    global _router
    if _router is None:
        _router = IntentRouter()
    return _router


def route_query(user_query: str) -> RouteResult:
    """Convenience function to route a query."""
    return get_intent_router().classify_domain(user_query)
