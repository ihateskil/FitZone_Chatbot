"""FastAPI service for deploying the FitZone agent on Render."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import Iterator

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.config import APP_NAME, DISCLAIMER, GROQ_API_KEY
from src.auth import _get_ready_app, _verify_api_key
from src.fitness_agent import ChatTurn, run_agent_full, stream_agent, warmup_agent
from src.lift_parser import LiftParser, is_lift_log as check_lift_log
from src.session_store import SessionStore
from src.progressor import recommend_progression
from src.formula_registry import format_formula_detail, search_formulas
from src.recovery import assess_recovery, compute_weekly_volumes, recovery_context_for_agent
from src.personality import list_personalities, PersonalityMode
from src.routes_nutrition import router as nutrition_router
from src.routes_formulas import router as formula_router
from src.routes_exercises import router as exercise_router
from src.logging_utils import setup_logging

setup_logging()


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    session_id: str = Field(default="default", min_length=1, max_length=64)
    science_mode: bool = Field(default=False, description="Enable formula transparency / show-your-work mode")
    personality: str = Field(default="coach", description="Personality mode: coach, drill_sergeant, science_professor, zen_guide")





@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = False
    app.state.startup_error = None

    if not GROQ_API_KEY:
        app.state.startup_error = "GROQ_API_KEY is not configured."
    else:
        fitzone_api_key = os.getenv("FITZONE_API_KEY", "")
        if not fitzone_api_key or len(fitzone_api_key) < 16:
            app.state.startup_error = (
                "FITZONE_API_KEY is not configured or is too short (min 16 chars)."
            )
        else:
            try:
                warmup_agent()
                app.state.ready = True
            except Exception as exc:  # pragma: no cover - startup safety
                app.state.startup_error = str(exc)

    yield


app = FastAPI(
    title=f"{APP_NAME} API",
    version="1.0.0",
    description="FitZone fitness and nutrition assistant API.",
    lifespan=lifespan,
)

# Allow the React dev server and known HF Spaces origin.
# Credentials are not used (API key is in headers), so wildcard origins are safe here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",       # Vite dev server
        "http://localhost:3000",       # CRA / other local dev
        "https://ihateskil-fitzone-chatbot.hf.space",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": APP_NAME,
        "status": "ok",
        "message": "FitZone API is running.",
    }


@app.get("/health")
def health() -> dict[str, object]:
    if not getattr(app.state, "ready", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=getattr(app.state, "startup_error", "Service is not ready."),
        )
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, object]:
    """Deep readiness check — verifies dependencies are functional."""
    if not getattr(app.state, "ready", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=getattr(app.state, "startup_error", "Service is not ready."),
        )
    return {"status": "ok", "message": "All dependencies operational."}


class ChatResponse(BaseModel):
    response: str
    latency_ms: float
    blocked: bool = False
    block_reason: str | None = None
    in_scope: bool = True
    lift_logged: bool = False
    progression_hint: str | None = None
    science_mode: bool = False





@app.post("/v1/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    _: None = Depends(_verify_api_key),
    _app: FastAPI = Depends(_get_ready_app),
) -> ChatResponse:
    history = [ChatTurn(role=turn.role, content=turn.content) for turn in payload.history]
    response = run_agent_full(payload.message, history=history)
    return ChatResponse(
        response=response.text,
        latency_ms=response.latency_ms,
        blocked=response.blocked,
        block_reason=response.block_reason,
        in_scope=response.in_scope,
        lift_logged=response.lift_logged,
        progression_hint=response.progression_hint,
        science_mode=payload.science_mode,
    )


@app.post("/v1/chat/stream")
def chat_stream(
    payload: ChatRequest,
    _: None = Depends(_verify_api_key),
    _app: FastAPI = Depends(_get_ready_app),
) -> StreamingResponse:
    history = [ChatTurn(role=turn.role, content=turn.content) for turn in payload.history]
    return StreamingResponse(
        _stream_chunks(payload.message, history, session_id=payload.session_id),
        media_type="text/event-stream; charset=utf-8",
    )




# ---------------------------------------------------------------------------
# Lift Tracking Endpoints
# ---------------------------------------------------------------------------

_lift_store = SessionStore()


class LiftLogRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1, max_length=64)
    science_mode: bool = Field(default=False, description="Enable formula transparency / show-your-work mode")
    personality: str = Field(default="coach", description="Personality mode: coach, drill_sergeant, science_professor, zen_guide")
    entry: str = Field(min_length=1, max_length=2000, description="Natural-language lift log, e.g. 'bench 185x8 185x6 190x5'")


class LiftLogResponse(BaseModel):
    logged: bool
    lifts: list[dict]
    session_id: str


@app.post("/v1/lift/log", response_model=LiftLogResponse)
def log_lift(
    payload: LiftLogRequest,
    _: None = Depends(_verify_api_key),
    _app: FastAPI = Depends(_get_ready_app),
) -> LiftLogResponse:
    """Log a workout entry from natural-language text."""
    from src.progressor import _lift_to_dict
    parsed = LiftParser.parse(payload.entry)
    if not parsed:
        return LiftLogResponse(logged=False, lifts=[], session_id=payload.session_id)
    result = _lift_store.log_lifts(payload.session_id, parsed)
    return LiftLogResponse(
        logged=True,
        lifts=result.get("lifts", []),
        session_id=payload.session_id,
    )


class LiftHistoryResponse(BaseModel):
    exercise: str
    entries: list[dict]
    session_id: str


@app.get("/v1/lift/history/{exercise}", response_model=LiftHistoryResponse)
def lift_history(
    exercise: str,
    session_id: str = "default",
    _: None = Depends(_verify_api_key),
    _app: FastAPI = Depends(_get_ready_app),
) -> LiftHistoryResponse:
    """Get lift history for a specific exercise."""
    entries = _lift_store.get_exercise_history(session_id, exercise)
    return LiftHistoryResponse(exercise=exercise, entries=entries, session_id=session_id)


class ProgressionResponse(BaseModel):
    exercise: str
    current_1rm: float
    recommended_weight: float
    recommended_reps: int
    recommended_sets: int
    reasoning: str
    irv: float
    irv_status: str


@app.get("/v1/lift/recommend/{exercise}", response_model=ProgressionResponse)
def lift_recommend(
    exercise: str,
    session_id: str = "default",
    _: None = Depends(_verify_api_key),
    _app: FastAPI = Depends(_get_ready_app),
) -> ProgressionResponse:
    """Get progression recommendation for an exercise based on logged history."""
    from src.progressor import ProgressionRecommendation
    entries = _lift_store.get_exercise_history(session_id, exercise)
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lift history found for '{exercise}'.",
        )
    last_sets = entries[-1].get("sets", [])
    rec = recommend_progression(exercise, last_sets)
    return ProgressionResponse(
        exercise=rec.exercise,
        current_1rm=rec.current_1rm,
        recommended_weight=rec.recommended_weight,
        recommended_reps=rec.recommended_reps,
        recommended_sets=rec.recommended_sets,
        reasoning=rec.reasoning,
        irv=rec.irv,
        irv_status=rec.irv_status,
    )



# ---------------------------------------------------------------------------
# Recovery & Fatigue Endpoints
# ---------------------------------------------------------------------------

class RecoveryResponse(BaseModel):
    acute_volume: float
    chronic_volume: float
    acwr: float
    risk_level: str
    recommendation: str
    deload_recommended: bool


@app.get("/v1/recovery", response_model=RecoveryResponse)
def get_recovery(
    session_id: str = "default",
    _: None = Depends(_verify_api_key),
    _app: FastAPI = Depends(_get_ready_app),
) -> RecoveryResponse:
    """Get recovery and fatigue assessment based on logged workout history."""
    volumes = compute_weekly_volumes(_lift_store, session_id)
    status = assess_recovery(volumes)
    return RecoveryResponse(
        acute_volume=status.acute_volume,
        chronic_volume=status.chronic_volume,
        acwr=status.acwr,
        risk_level=status.risk_level,
        recommendation=status.recommendation,
        deload_recommended=status.deload_recommended,
    )



# ---------------------------------------------------------------------------
# Personality Modes
# ---------------------------------------------------------------------------

class PersonalityInfoResponse(BaseModel):
    personalities: list[dict[str, str]]


@app.get("/v1/personalities", response_model=PersonalityInfoResponse)
def get_personalities(
    _: None = Depends(_verify_api_key),
    _app: FastAPI = Depends(_get_ready_app),
) -> PersonalityInfoResponse:
    """List all available personality modes."""
    return PersonalityInfoResponse(personalities=list_personalities())

# Include routers
app.include_router(nutrition_router)
app.include_router(formula_router)
app.include_router(exercise_router)


def _stream_chunks(
    message: str,
    history: list[ChatTurn],
    session_id: str = "default",
) -> Iterator[str]:
    for chunk in stream_agent(message, history=history, session_id=session_id):
        yield chunk
