"""
FitZone Fitness AI Agent — scoped guardrail/router, RAG retrieval, and LLM generation.
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.config import (
    AGENT_SYSTEM_PROMPT,
    GROQ_FAST_MODEL,
    GROQ_MODEL,
    INTENT_CLASSIFIER_PROMPT,
    KNOWLEDGE_DB_DIR,
    KNOWLEDGE_MATCH_THRESHOLD,
    LLM_TEMPERATURE,
    MAX_CONTEXT_CHARS,
    MAX_HISTORY_TURNS,
    OUT_OF_SCOPE_RESPONSE,
    RETRIEVAL_TOP_K,
)
from src.input_validation import ValidationResult, validate_user_input
from src.knowledge_retriever import KnowledgeRetriever
from src.logging_utils import log_event, timed_operation
from src.open_food_facts import OpenFoodFactsClient
from src.retry_utils import with_retries
from src.safety import SafetyCheck, SafetyLevel, check_safety

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
SOURCE_TAG_PATTERN = re.compile(r"^\[Source:[^\]]+\]\s*\n?", re.MULTILINE)

Role = Literal["user", "assistant"]


@dataclass
class ChatTurn:
    role: Role
    content: str


@dataclass
class AgentResponse:
    text: str
    blocked: bool = False
    block_reason: str | None = None
    latency_ms: float = 0.0
    in_scope: bool = True


def _sanitize_reference_context(context: str) -> str:
    cleaned = SOURCE_TAG_PATTERN.sub("", context)
    cleaned = re.sub(
        r"^(KNOWLEDGE BASE|OPEN FOOD FACTS API|REFERENCE CONTEXT).*$",
        "",
        cleaned,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not cleaned or "no matching reference" in cleaned.lower():
        return ""
    return cleaned


def _truncate_history(history: list[ChatTurn]) -> list[ChatTurn]:
    if len(history) <= MAX_HISTORY_TURNS * 2:
        return history
    return history[-(MAX_HISTORY_TURNS * 2) :]


# ---------------------------------------------------------------------------
# Intent router
# ---------------------------------------------------------------------------


class IntentRouter:
    FITNESS_KEYWORDS = frozenset(
        {
            "gym", "fitness", "workout", "exercise", "training", "lift", "lifting",
            "squat", "deadlift", "bench", "cardio", "rep", "reps", "set", "sets",
            "muscle", "hypertrophy", "strength", "calorie", "calories", "macro",
            "macros", "protein", "carb", "carbs", "fat", "nutrition", "diet",
            "meal", "bmr", "tdee", "1rm", "volume", "load", "bulk", "cut",
            "lean", "weight", "bodyweight", "supplement", "creatine", "preworkout",
            "recovery", "stretch", "warmup", "cooldown", "hiit", "aerobic",
            "anaerobic", "metabolism", "hydration", "chicken", "apple",
            # Training methodology
            "ppl", "deload", "rpe", "rir", "amrap", "emom", "superset",
            "dropset", "myo", "overload", "periodization", "mesocycle",
            # Body composition
            "recomp", "shred", "gains", "physique", "bodybuilding", "powerlifting",
            # Supplements & recovery
            "whey", "casein", "bcaa", "eaa", "caffeine", "sleep", "soreness",
            "doms", "foam", "roller", "mobility",
        }
    )
    GREETING_KEYWORDS = frozenset(
        {
            "hey", "hi", "hello", "sup", "yo", "morning", "evening", "afternoon",
            "thanks", "thank", "bye", "goodbye", "cheers", "appreciate", "coach",
            "bro", "dude", "man",
        }
    )
    OUT_OF_SCOPE_KEYWORDS = frozenset(
        {
            "python", "javascript", "code", "programming", "weather", "stock",
            "election", "politics", "movie", "sql", "kubernetes", "docker", "react",
            "homework", "essay", "poem", "story", "recipe", "travel", "flight",
            "crypto", "bitcoin", "algebra", "calculus", "history",
        }
    )

    def __init__(self, model: str = GROQ_FAST_MODEL) -> None:
        self._llm: ChatGroq | None = None
        self._model = model

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(TOKEN_PATTERN.findall(text.lower()))

    @classmethod
    def heuristic_classify(cls, user_query: str) -> str | None:
        tokens = cls._tokenize(user_query)
        if tokens & cls.OUT_OF_SCOPE_KEYWORDS and not (tokens & cls.FITNESS_KEYWORDS):
            return "OUT_OF_SCOPE"
        if tokens & cls.FITNESS_KEYWORDS:
            return "IN_SCOPE"
        # Short greetings/pleasantries (< 3 tokens, all greeting) — skip LLM
        if len(tokens) < 3 and tokens & cls.GREETING_KEYWORDS and not (tokens & cls.OUT_OF_SCOPE_KEYWORDS):
            return "IN_SCOPE"
        # Longer queries with greeting mixed in — fall through to LLM
        if tokens & cls.GREETING_KEYWORDS and not (tokens & cls.OUT_OF_SCOPE_KEYWORDS):
            return "IN_SCOPE"
        return None

    def _get_llm(self) -> ChatGroq:
        if self._llm is None:
            self._llm = ChatGroq(model=self._model, temperature=0.0)
        return self._llm

    def classify(self, user_query: str) -> bool:
        heuristic = self.heuristic_classify(user_query)
        if heuristic == "OUT_OF_SCOPE":
            return False
        if heuristic == "IN_SCOPE":
            return True

        def _classify() -> bool:
            response = self._get_llm().invoke(
                [
                    SystemMessage(content=INTENT_CLASSIFIER_PROMPT),
                    HumanMessage(content=user_query),
                ]
            )
            label = (response.content or "").strip().upper()
            if "OUT_OF_SCOPE" in label:
                return False
            return "IN_SCOPE" in label

        return with_retries(_classify, label="intent_classifier")


# ---------------------------------------------------------------------------
# Generation layer
# ---------------------------------------------------------------------------


class FitnessAgent:
    def __init__(
        self,
        model: str = GROQ_MODEL,
        fast_model: str = GROQ_FAST_MODEL,
        temperature: float = LLM_TEMPERATURE,
        top_k: int = RETRIEVAL_TOP_K,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._llm: ChatGroq | None = None
        self._router = IntentRouter(model=fast_model)
        self._knowledge = KnowledgeRetriever(KNOWLEDGE_DB_DIR, top_k=top_k)
        self._food_client = OpenFoodFactsClient()
        self._pool = ThreadPoolExecutor(max_workers=2)

    def _get_llm(self) -> ChatGroq:
        if self._llm is None:
            self._llm = ChatGroq(model=self._model, temperature=self._temperature)
        return self._llm

    @staticmethod
    def _truncate_context(context: str) -> str:
        if len(context) <= MAX_CONTEXT_CHARS:
            return context
        truncated = context[:MAX_CONTEXT_CHARS].rsplit("\n", 1)[0]
        return truncated + "\n[…]"

    def _build_context(self, user_query: str) -> tuple[str, float]:
        knowledge_future = self._pool.submit(self._knowledge.retrieve, user_query)
        food_future = None
        if self._food_client.is_food_query(user_query):
            food_future = self._pool.submit(self._food_client.retrieve_context, user_query)

        sections: list[str] = []

        knowledge_context, knowledge_score = knowledge_future.result()
        # Only inject knowledge if it meets the similarity threshold
        if knowledge_score >= KNOWLEDGE_MATCH_THRESHOLD:
            sections.append(f"[TRAINING & SCIENCE NOTES]\n{knowledge_context}")

        if food_future is not None:
            food_context, food_found = food_future.result()
            if food_found:
                sections.append(f"[NUTRITION DATA]\n{food_context}")

        combined = "\n\n---\n\n".join(sections) if sections else ""
        return self._truncate_context(_sanitize_reference_context(combined)), knowledge_score

    def _build_messages(
        self,
        user_query: str,
        context: str,
        history: list[ChatTurn],
    ) -> list[BaseMessage]:
        messages: list[BaseMessage] = [SystemMessage(content=AGENT_SYSTEM_PROMPT.strip())]

        for turn in _truncate_history(history):
            if turn.role == "user":
                messages.append(HumanMessage(content=turn.content))
            else:
                messages.append(AIMessage(content=turn.content))

        # Build the final user message with context injection
        if context:
            user_prompt = (
                f"[INTERNAL CONTEXT — for your eyes only. Never reference these notes, "
                f"their existence, or where any information came from. Synthesize the data "
                f"naturally into your expert coaching response. Use specific numbers and "
                f"details from the notes when relevant.]\n\n"
                f"{context}\n\n"
                f"---\n\n"
                f"{user_query}"
            )
        else:
            user_prompt = user_query

        messages.append(HumanMessage(content=user_prompt))
        return messages

    def _preprocess(self, user_query: str) -> tuple[ValidationResult, SafetyCheck]:
        validation = validate_user_input(user_query)
        if not validation.ok:
            return validation, SafetyCheck(SafetyLevel.OK)
        safety = check_safety(validation.cleaned)
        return validation, safety

    def run(self, user_query: str, history: list[ChatTurn] | None = None) -> AgentResponse:
        start = time.perf_counter()
        history = history or []

        validation, safety = self._preprocess(user_query)
        if not validation.ok:
            return AgentResponse(
                text=validation.message,
                blocked=True,
                block_reason="validation",
                latency_ms=_elapsed_ms(start),
            )
        if safety.level != SafetyLevel.OK:
            return AgentResponse(
                text=safety.response or "",
                blocked=True,
                block_reason=safety.level.value,
                latency_ms=_elapsed_ms(start),
            )

        query = validation.cleaned
        if not self._router.classify(query):
            log_event("out_of_scope", query_len=len(query))
            return AgentResponse(
                text=OUT_OF_SCOPE_RESPONSE,
                in_scope=False,
                latency_ms=_elapsed_ms(start),
            )

        with timed_operation("build_context", query_len=len(query)) as timing:
            context, score = self._build_context(query)
            timing["knowledge_score"] = score

        messages = self._build_messages(query, context, history)

        def _generate() -> str:
            response = self._get_llm().invoke(messages)
            return (response.content or "").strip()

        try:
            text = with_retries(_generate, label="groq_generation")
        except RuntimeError:
            return AgentResponse(
                text=(
                    "I'm having trouble connecting right now. "
                    "Please try again in a moment."
                ),
                blocked=True,
                block_reason="llm_error",
                latency_ms=_elapsed_ms(start),
            )

        latency = _elapsed_ms(start)
        log_event("agent_response", query_len=len(query), latency_ms=latency, in_scope=True)
        return AgentResponse(text=text, latency_ms=latency)

    def stream(
        self, user_query: str, history: list[ChatTurn] | None = None
    ) -> Iterator[str]:
        """Stream response tokens. Yields full text on early blocks/errors."""
        history = history or []
        validation, safety = self._preprocess(user_query)

        if not validation.ok:
            yield validation.message
            return
        if safety.level != SafetyLevel.OK:
            yield safety.response or ""
            return

        query = validation.cleaned
        if not self._router.classify(query):
            yield OUT_OF_SCOPE_RESPONSE
            return

        context, _ = self._build_context(query)
        messages = self._build_messages(query, context, history)

        stream_completed = False
        try:
            for chunk in self._get_llm().stream(messages):
                content = chunk.content
                if content:
                    yield content
            stream_completed = True
        except Exception as exc:
            log_event("stream_error", error=str(exc))
            yield "I'm having trouble connecting right now. Please try again in a moment."
        finally:
            if not stream_completed:
                log_event("stream_incomplete", query_len=len(query))


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_agent: FitnessAgent | None = None


def get_agent() -> FitnessAgent:
    global _agent
    if _agent is None:
        _agent = FitnessAgent()
    return _agent


def warmup_agent() -> FitnessAgent:
    return get_agent()


def run_agent(
    user_query: str,
    history: list[ChatTurn] | None = None,
) -> str:
    """Convenience wrapper returning plain text (backward compatible)."""
    return get_agent().run(user_query, history=history).text


def run_agent_full(
    user_query: str,
    history: list[ChatTurn] | None = None,
) -> AgentResponse:
    return get_agent().run(user_query, history=history)


def stream_agent(
    user_query: str,
    history: list[ChatTurn] | None = None,
) -> Iterator[str]:
    return get_agent().stream(user_query, history=history)
