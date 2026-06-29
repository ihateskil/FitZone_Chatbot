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

# Note: re is imported once here; _re alias removed from line ~98

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.config import (
    AGENT_SYSTEM_PROMPT,
    GROQ_FAST_MODEL,
    GROQ_MODEL,
    KNOWLEDGE_DB_DIR,
    KNOWLEDGE_MATCH_THRESHOLD,
    LLM_TEMPERATURE,
    MAX_CONTEXT_CHARS,
    MAX_HISTORY_TURNS,
    MAX_MESSAGE_LENGTH,
    OUT_OF_SCOPE_RESPONSE,
    RETRIEVAL_TOP_K,
)
from src.input_validation import ValidationResult, validate_user_input
from src.knowledge_retriever import KnowledgeRetriever
from src.logging_utils import log_event, timed_operation
from src.open_food_facts import OpenFoodFactsClient
from src.pubmed_client import PubMedClient
from src.retry_utils import with_retries
from src.safety import SafetyCheck, SafetyLevel, check_safety
from src.lift_parser import LiftParser, is_lift_log
from src.session_store import SessionStore
from src.progressor import recommend_progression, volume_load
from src.formula_registry import SCIENCE_MODE_PROMPT_ADDITION, COACH_MODE_PROMPT_ADDITION
from src.recovery import recovery_context_for_agent
from src.personality import get_personality_prompt
from src.intent_router import get_intent_router, route_query
from src.nutrition_retriever import get_nutrition_retriever
from src.formula_calculator import get_formula_calculator
from src.exercise_retriever import get_exercise_retriever
from src.user_profile import ProfileStore, UserProfile
from src.weekly_tracker import compute_weekly_summaries, compute_trends, format_trend_context
from src.adaptive_planner import AdaptivePlanner

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
    lift_logged: bool = False
    progression_hint: str | None = None
    science_mode: bool = False
    personality: str = "coach"


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
# User Profile Extraction from Conversation (fallback for contexts without
# ProfileStore)
# ---------------------------------------------------------------------------

_WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:kg|kgs|lbs?|pounds?)", re.IGNORECASE)
_HEIGHT_CM_RE = re.compile(r"(\d{2,3})\s*(?:cm|centimeter)", re.IGNORECASE)
_HEIGHT_FT_RE = re.compile(r"(\d)'\s*(\d{1,2})", re.IGNORECASE)
_AGE_RE = re.compile(r"(\d{1,2})\s*(?:years?\s*old|yr|yo)", re.IGNORECASE)
_GENDER_RE = re.compile(r"\b(male|female|man|woman|guy|girl|boy)\b", re.IGNORECASE)
_BODYFAT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:body\s*fat|bf|bodyfat)", re.IGNORECASE)
_GOAL_RE = re.compile(r"\b(bulk|bulking|cut|cutting|lean\s*bulk|recomp|maintain|lose\s*weight|build\s*muscle|gain\s*muscle|shred|get\s*stronger|hypertrophy|strength)\b", re.IGNORECASE)


def _extract_user_profile(history: list[ChatTurn]) -> dict[str, str]:
    """Extract key user metrics from conversation history for context injection."""
    if not history:
        return {}

    text = " ".join(t.content for t in history if t.role == "user")
    profile: dict[str, str] = {}

    m = _WEIGHT_RE.search(text)
    if m:
        val = float(m.group(1))
        unit = "kg" if "kg" in m.group(0).lower() else "lbs"
        profile["weight"] = f"{val} {unit}"

    m = _HEIGHT_CM_RE.search(text)
    if m:
        profile["height"] = f"{m.group(1)} cm"

    m = _HEIGHT_FT_RE.search(text)
    if m:
        feet, inches = int(m.group(1)), int(m.group(2))
        profile["height"] = f"{feet}'{inches}\" ({round(feet*30.48 + inches*2.54)} cm)"

    m = _AGE_RE.search(text)
    if m:
        profile["age"] = f"{m.group(1)} years"

    m = _GENDER_RE.search(text)
    if m:
        g = m.group(1).lower()
        if g in ("male", "man", "guy", "boy"):
            profile["gender"] = "male"
        elif g in ("female", "woman", "girl"):
            profile["gender"] = "female"

    m = _BODYFAT_RE.search(text)
    if m:
        profile["body_fat"] = f"{m.group(1)}%"

    m = _GOAL_RE.search(text)
    if m:
        profile["goal"] = m.group(1)

    return profile

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
        self._router = get_intent_router()
        self._knowledge = KnowledgeRetriever(KNOWLEDGE_DB_DIR, top_k=top_k)
        self._food_client = OpenFoodFactsClient()
        self._pubmed_client = PubMedClient()
        self._session_store = SessionStore()
        self._profile_store = ProfileStore()
        self._planner = AdaptivePlanner()
        self._pool = ThreadPoolExecutor(max_workers=4)
        self._nutrition = get_nutrition_retriever()
        self._formula_calc = get_formula_calculator()
        self._exercises = get_exercise_retriever()

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

    def _build_context(self, user_query: str, session_id: str = "default", profile: UserProfile | None = None) -> tuple[str, float]:
        knowledge_future = self._pool.submit(self._knowledge.retrieve, user_query)
        food_future = None
        pubmed_future = None
        trends_future = None
        # Use domain routing to decide which retrievers to invoke
        route_result = route_query(user_query)
        if route_result.domain in ("nutrition_lookup", "general_fitness"):
            food_future = self._pool.submit(self._food_client.retrieve_context, user_query)
        if PubMedClient.is_research_query(user_query):
            pubmed_future = self._pool.submit(self._pubmed_client.retrieve_context, user_query)

        # Compute weekly trends in parallel if we have a session
        if self._session_store.get_session(session_id) is not None:
            trends_future = self._pool.submit(
                self._compute_trends_for_context, session_id
            )

        sections: list[str] = []

        knowledge_context, knowledge_score = knowledge_future.result()
        # Only inject knowledge if it meets the similarity threshold
        if knowledge_score >= KNOWLEDGE_MATCH_THRESHOLD:
            sections.append(f"[TRAINING & SCIENCE NOTES]\n{knowledge_context}")

        if food_future is not None:
            food_context, food_found = food_future.result()
            if food_found:
                sections.append(f"[NUTRITION DATA]\n{food_context}")

        if pubmed_future is not None:
            pubmed_context, pubmed_found = pubmed_future.result()
            if pubmed_found:
                sections.append(pubmed_context)

        # Add nutrition knowledge base context
        nutrition_context = self._nutrition.format_for_llm(
            self._nutrition.search(user_query, top_k=3)
        )
        if nutrition_context:
            sections.append(nutrition_context)

        # Inject formula context for calculation queries
        if route_result.domain == "calculation":
            formula_ctx = self._build_formula_context(user_query)
            if formula_ctx:
                sections.append(formula_ctx)

        # Inject exercise context for exercise lookup queries
        if route_result.domain == "exercise_lookup":
            exercise_ctx = self._build_exercise_context(user_query)
            if exercise_ctx:
                sections.append(exercise_ctx)

        # Inject recovery/fatigue context if session has lifts (must happen BEFORE building combined)
        try:
            recovery_ctx = recovery_context_for_agent(self._session_store, session_id)
            if recovery_ctx:
                sections.append(f"[RECOVERY]\n{recovery_ctx}")
        except Exception:
            pass  # Recovery context is optional

        # Inject user profile context
        if profile is not None:
            profile_ctx = profile.format_for_context()
            if profile_ctx:
                sections.append(profile_ctx)

        # Inject weekly trends + adaptive recommendations
        if trends_future is not None:
            try:
                trend_ctx, rec_ctx = trends_future.result()
                if trend_ctx:
                    sections.append(trend_ctx)
                if rec_ctx:
                    sections.append(rec_ctx)
            except Exception:
                pass

        combined = "\n\n---\n\n".join(sections) if sections else ""
        return self._truncate_context(_sanitize_reference_context(combined)), knowledge_score

    def _compute_trends_for_context(self, session_id: str) -> tuple[str, str]:
        """Compute weekly trends + adaptive recommendations for context injection."""
        summaries = compute_weekly_summaries(self._session_store)
        if not summaries:
            return "", ""
        trend = compute_trends(summaries)
        trend_ctx = format_trend_context(trend)
        profile = self._profile_store.load(session_id)
        rec = self._planner.analyze(profile, trend)
        rec_ctx = rec.format_for_context()
        return trend_ctx, rec_ctx

    def _build_exercise_context(self, user_query: str) -> str | None:
        """Build exercise context for exercise lookup queries."""
        results = self._exercises.search(user_query, top_k=5)
        if not results:
            return None
        return self._exercises.format_for_llm(results)

    def _build_formula_context(self, user_query: str) -> str | None:
        """Build formula context for calculation queries."""
        import re
        # Try to extract numbers from the query
        numbers = [float(m) for m in re.findall(r"\d+\.?\d*", user_query)]
        if not numbers:
            return None

        # Determine which formula to use based on keywords
        q = user_query.lower()
        context_parts = []

        if any(w in q for w in ["bmr", "metabolic", "metabolism"]):
            context_parts.append("Available BMR formulas: Mifflin-St Jeor (most accurate), Katch-McArdle (if BF% known), Harris-Benedict (legacy)")
            context_parts.append("Mifflin-St Jeor Men: BMR = (10 x weight_kg) + (6.25 x height_cm) - (5 x age) + 5")
            context_parts.append("Mifflin-St Jeor Women: BMR = (10 x weight_kg) + (6.25 x height_cm) - (5 x age) - 161")

        if any(w in q for w in ["tdee", "calorie", "calories", "maintenance"]):
            context_parts.append("TDEE = BMR x Activity Multiplier")
            context_parts.append("Multipliers: Sedentary=1.2, Light=1.375, Moderate=1.55, Very=1.725, Extreme=1.9")

        if any(w in q for w in ["1rm", "one rep", "one-rep", "max"]):
            context_parts.append("1RM formulas: Brzycki (preferred), Epley, Lander")
            context_parts.append("Brzycki: 1RM = weight / (1.0278 - 0.0278 x reps)")
            context_parts.append("Epley: 1RM = weight x (1 + reps/30)")

        if any(w in q for w in ["body fat", "bf%", "bodyfat"]):
            context_parts.append("Navy Body Fat Formula requires: waist_cm, neck_cm, height_cm (+ hip_cm for women)")

        if any(w in q for w in ["protein"]):
            context_parts.append("Protein targets: General health=0.8g/kg, Endurance=1.2-1.4g/kg, Muscle building=1.6-2.2g/kg, Cutting=2.0-2.4g/kg")

        if context_parts:
            return "[FORMULA REFERENCE]\n" + "\n".join(context_parts)
        return None

    def _build_messages(
        self,
        user_query: str,
        context: str,
        history: list[ChatTurn],
        profile: UserProfile | None = None,
        science_mode: bool = False,
        personality: str = "coach",
    ) -> list[BaseMessage]:
        system_prompt = AGENT_SYSTEM_PROMPT.strip()
        # Apply personality mode
        system_prompt += get_personality_prompt(personality)
        # Apply science/coach mode
        if science_mode:
            system_prompt += SCIENCE_MODE_PROMPT_ADDITION
        else:
            system_prompt += COACH_MODE_PROMPT_ADDITION
        # Inject user profile into system prompt (persistent profile preferred, fallback to extraction)
        if profile is not None and any([profile.weight_kg, profile.age, profile.gender, profile.primary_goal]):
            system_prompt += "\n\n## User Profile\n" + profile.format_for_context().replace("## User Profile\n", "") + "\n(Use these details in calculations and recommendations.)"
        else:
            user_profile = _extract_user_profile(history)
            if user_profile:
                profile_lines = [f"- **{k.replace('_', ' ').title()}**: {v}" for k, v in user_profile.items()]
                system_prompt += "\n\n## User Profile (extracted from conversation)\n" + "\n".join(profile_lines) + "\n(Use these details in calculations and recommendations.)"

        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]

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

    def _process_lift_log(
        self,
        user_query: str,
        session_id: str = "default",
    ) -> tuple[list, str | None]:
        """Detect lift logs, store them, and build progression context.

        Returns:
            (parsed_lifts, progression_context) - parsed lifts and optional
            progression recommendation text for context injection.
        """
        if not is_lift_log(user_query):
            return [], None

        parsed = LiftParser.parse(user_query)
        if not parsed:
            return [], None

        # Log the lifts
        self._session_store.log_lifts(session_id, parsed)

        # Build progression context for each exercise
        progression_parts: list[str] = []
        for lift in parsed:
            history = self._session_store.get_all_exercise_history(lift.exercise)
            if history:
                last_entry = history[-1]
                last_sets = last_entry.get("sets", [])
                rec = recommend_progression(lift.exercise, last_sets)
                progression_parts.append(
                    f"[PROGRESSION DATA for {rec.exercise}]\n"
                    f"Estimated 1RM: {rec.current_1rm}\n"
                    f"IRV: {rec.irv} ({rec.irv_status})\n"
                    f"Next session recommendation: {rec.recommended_weight} x {rec.recommended_reps} x {rec.recommended_sets}\n"
                    f"Reasoning: {rec.reasoning}"
                )

        progression_ctx = "\n\n".join(progression_parts) if progression_parts else None
        return parsed, progression_ctx

    def run(self, user_query: str, history: list[ChatTurn] | None = None, science_mode: bool = False, personality: str = "coach", session_id: str = "default") -> AgentResponse:
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
        if not self._router.classify_scope(query):
            log_event("out_of_scope", query_len=len(query))
            return AgentResponse(
                text=OUT_OF_SCOPE_RESPONSE,
                in_scope=False,
                latency_ms=_elapsed_ms(start),
            )

        # Detect and process lift logs
        lift_logged = False
        progression_hint = None
        parsed_lifts, progression_ctx = self._process_lift_log(query, session_id)
        if parsed_lifts:
            lift_logged = True
            progression_hint = progression_ctx

        # Update persistent user profile from this conversation turn
        profile = self._profile_store.update_from_conversation(session_id, query)

        with timed_operation("build_context", query_len=len(query)) as timing:
            context, score = self._build_context(query, session_id=session_id, profile=profile)
            timing["knowledge_score"] = score

        # Append progression context if available
        if progression_ctx:
            if context:
                context = context + "\n\n---\n\n" + progression_ctx
            else:
                context = progression_ctx

        messages = self._build_messages(query, context, history, profile=profile, science_mode=science_mode, personality=personality)

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
        text = _truncate_response(text)
        log_event("agent_response", query_len=len(query), latency_ms=latency, in_scope=True, lift_logged=lift_logged)
        return AgentResponse(text=text, latency_ms=latency, lift_logged=lift_logged, progression_hint=progression_hint, science_mode=science_mode)

    def stream(
        self,
        user_query: str,
        history: list[ChatTurn] | None = None,
        science_mode: bool = False,
        personality: str = "coach",
        session_id: str = "default",
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
        if not self._router.classify_scope(query):
            yield OUT_OF_SCOPE_RESPONSE
            return

        # Detect and process lift logs — mirrors run() so streaming also records workouts
        parsed_lifts, progression_ctx = self._process_lift_log(query, session_id)

        # Update persistent user profile from this conversation turn
        profile = self._profile_store.update_from_conversation(session_id, query)

        context, _ = self._build_context(query, session_id=session_id, profile=profile)

        # Append progression context if a lift was just logged
        if progression_ctx:
            context = (context + "\n\n---\n\n" + progression_ctx) if context else progression_ctx

        messages = self._build_messages(
            query, context, history, profile=profile, science_mode=science_mode, personality=personality
        )

        if parsed_lifts:
            log_event("lift_logged_stream", count=len(parsed_lifts), session_id=session_id)

        stream_completed = False
        acc_len = 0
        try:
            for chunk in self._get_llm().stream(messages):
                content = chunk.content or ""
                if not content:
                    continue
                remaining = MAX_MESSAGE_LENGTH - acc_len
                if remaining <= 0:
                    break
                if len(content) > remaining:
                    yield content[:remaining]
                    break
                yield content
                acc_len += len(content)
            stream_completed = True
        except Exception as exc:
            log_event("stream_error", error=str(exc))
            yield "I'm having trouble connecting right now. Please try again in a moment."
        finally:
            if not stream_completed:
                log_event("stream_incomplete", query_len=len(query))


def _truncate_response(text: str) -> str:
    if len(text) <= MAX_MESSAGE_LENGTH:
        return text
    cut = MAX_MESSAGE_LENGTH - 3
    truncated = text[:cut].rsplit(". ", 1)[0]
    if len(truncated) <= cut // 2:
        truncated = text[:cut]
    return truncated.strip() + "..."


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
    science_mode: bool = False,
    personality: str = "coach",
) -> str:
    """Convenience wrapper returning plain text (backward compatible)."""
    return get_agent().run(user_query, history=history, science_mode=science_mode, personality=personality).text


def run_agent_full(
    user_query: str,
    history: list[ChatTurn] | None = None,
    science_mode: bool = False,
    personality: str = "coach",
) -> AgentResponse:
    return get_agent().run(user_query, history=history, science_mode=science_mode, personality=personality)


def stream_agent(
    user_query: str,
    history: list[ChatTurn] | None = None,
    science_mode: bool = False,
    personality: str = "coach",
    session_id: str = "default",
) -> Iterator[str]:
    return get_agent().stream(
        user_query,
        history=history,
        science_mode=science_mode,
        personality=personality,
        session_id=session_id,
    )
