"""FastAPI service for deploying the FitZone agent on Render."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import Iterator

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import APP_NAME, DISCLAIMER, GROQ_API_KEY
from fitness_agent import ChatTurn, run_agent_full, stream_agent, warmup_agent
from logging_utils import setup_logging

setup_logging()


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


def _require_ready(app: FastAPI) -> None:
    """Raise 503 if the agent failed to warm up."""
    if not getattr(app.state, "ready", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=getattr(app.state, "startup_error", "Service is not ready."),
        )


def _verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    fitzone_api_key = os.getenv("FITZONE_API_KEY", "")

    if not fitzone_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    if x_api_key != fitzone_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = False
    app.state.startup_error = None

    if not GROQ_API_KEY:
        app.state.startup_error = "GROQ_API_KEY is not configured."
        # Fail fast — never serve traffic without a working LLM.
        raise RuntimeError(app.state.startup_error)

    fitzone_api_key = os.getenv("FITZONE_API_KEY", "")
    if not fitzone_api_key or len(fitzone_api_key) < 16:
        app.state.startup_error = (
            "FITZONE_API_KEY is not configured or is too short (min 16 chars)."
        )
        raise RuntimeError(app.state.startup_error)

    try:
        warmup_agent()
    except Exception as exc:  # pragma: no cover - startup safety
        app.state.startup_error = str(exc)
        # Let lifespan yield so /health can fail, but /chat will 503 via _require_ready.
        yield
        return

    app.state.ready = True
    yield


app = FastAPI(
    title=f"{APP_NAME} API",
    version="1.0.0",
    description="FitZone fitness and nutrition assistant API.",
    lifespan=lifespan,
)

# Allow the React dev server (localhost) and HF Spaces to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.post("/v1/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    _: None = Depends(_verify_api_key),
    app: FastAPI = Depends(lambda: app),
) -> ChatResponse:
    _require_ready(app)
    history = [ChatTurn(role=turn.role, content=turn.content) for turn in payload.history]
    response = run_agent_full(payload.message, history=history)
    return ChatResponse(
        response=response.text,
        latency_ms=response.latency_ms,
        blocked=response.blocked,
        block_reason=response.block_reason,
        in_scope=response.in_scope,
    )


@app.post("/v1/chat/stream")
def chat_stream(
    payload: ChatRequest,
    _: None = Depends(_verify_api_key),
    app: FastAPI = Depends(lambda: app),
) -> StreamingResponse:
    _require_ready(app)
    history = [ChatTurn(role=turn.role, content=turn.content) for turn in payload.history]

    def _generate() -> Iterator[str]:
        for chunk in stream_agent(payload.message, history=history):
            yield chunk

    return StreamingResponse(_generate(), media_type="text/event-stream; charset=utf-8")
    disclaimer: str = DISCLAIMER
