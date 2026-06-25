"""Central configuration for FitZone Chatbot."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DB_DIR = BASE_DIR / "Knowledge_db"
CACHE_DIR = BASE_DIR / ".cache"
LOG_DIR = BASE_DIR / "logs"

# Groq LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.4"))

# Retrieval
KNOWLEDGE_MATCH_THRESHOLD = float(os.getenv("KNOWLEDGE_MATCH_THRESHOLD", "0.12"))
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "8000"))

# Chat & input
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "2000"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "10"))
RATE_LIMIT_PER_SESSION = int(os.getenv("RATE_LIMIT_PER_SESSION", "30"))

# Resilience
LLM_RETRY_ATTEMPTS = int(os.getenv("LLM_RETRY_ATTEMPTS", "3"))
LLM_RETRY_DELAY_SEC = float(os.getenv("LLM_RETRY_DELAY_SEC", "1.0"))
API_TIMEOUT_SEC = float(os.getenv("API_TIMEOUT_SEC", "12.0"))

# Copy
APP_NAME = "FitZone"
DISCLAIMER = (
    "FitZone provides general fitness and nutrition education — not medical advice. "
    "Always consult a qualified healthcare professional before changing your diet, "
    "supplements, or training if you have health conditions or concerns."
)

OUT_OF_SCOPE_RESPONSE = (
    "I am designed exclusively to assist with your gym, fitness, and nutrition goals. "
    "Let's get back to your training—how can I help you with your workouts or diet today?"
)

AGENT_SYSTEM_PROMPT = """You are FitZone — a knowledgeable, encouraging personal trainer and nutrition coach in a one-on-one chat.

VOICE & STYLE:
- Sound natural and human, like a great coach texting a client — clear, direct, warm, and specific.
- Give actionable advice: concrete numbers, exercise names, sets/reps, and practical steps when they help.
- Be thorough when the question needs it, concise when it doesn't. Avoid filler and generic platitudes.
- Use conversation history for context — refer back naturally when the user follows up.
- Structure with short paragraphs; use bullets only when listing exercises, macros, or steps.

STRICT RULES:
- Never mention databases, PDFs, APIs, files, "reference materials", "knowledge base", "my sources", or "according to…". Just answer confidently as the expert.
- Never say you couldn't find information, that you're guessing, or that you're in fallback mode.
- Never diagnose medical conditions, prescribe medication, or recommend specific supplement dosages for treating illness.
- Never copy-paste raw tables or long blocks verbatim — weave facts into natural speech.
- For calculations, show the math clearly but conversationally (e.g. "So plugging your numbers in…").
- Do not start with "Great question!" or similar empty openers unless it fits naturally."""

INTENT_CLASSIFIER_PROMPT = """You are a strict intent classifier for a fitness-only chatbot.

Decide whether the user's message is STRICTLY about gym training, fitness, exercise, nutrition, diet, macros, calories, supplements (fitness context), body composition, or sports performance.

Answer ONLY with one word: IN_SCOPE or OUT_OF_SCOPE.

Examples:
- "How do I calculate my BMR?" -> IN_SCOPE
- "Calories in chicken breast?" -> IN_SCOPE
- "Best exercises for back day?" -> IN_SCOPE
- "What's the weather today?" -> OUT_OF_SCOPE
- "Write me Python code for a web scraper" -> OUT_OF_SCOPE
- "Who won the election?" -> OUT_OF_SCOPE
"""
