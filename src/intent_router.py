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
    # Fitness-related health issues
    "overtraining", "overtrain", "plateau", "stagnation", "doms",
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
    "python", "javascript", "code", "programming", "weather", "stock",
    "election", "politics", "movie", "sql", "kubernetes", "docker", "react",
    "homework", "essay", "poem", "story", "recipe", "travel", "flight",
    "crypto", "bitcoin", "algebra", "calculus", "history", "write", "coding",
    "software", "app", "website", "database", "server", "deploy",
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
