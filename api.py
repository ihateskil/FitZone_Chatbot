"""FastAPI service for deploying the FitZone agent on Render."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import Iterator

from fastapi import Depends, FastAPI, Header, HTTPException, status
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
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    latency_ms: float
    blocked: bool = False
    block_reason: str | None = None
    in_scope: bool = True
    disclaimer: str = DISCLAIMER


def _verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    fitzone_api_key = os.getenv("FITZONE_API_KEY", "")

    if not fitzone_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FITZONE_API_KEY is not configured on the server.",
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
        yield
        return

    try:
        warmup_agent()
    except Exception as exc:  # pragma: no cover - startup safety
        app.state.startup_error = str(exc)
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


@app.post("/v1/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, _: None = Depends(_verify_api_key)) -> ChatResponse:
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
def chat_stream(payload: ChatRequest, _: None = Depends(_verify_api_key)) -> StreamingResponse:
    history = [ChatTurn(role=turn.role, content=turn.content) for turn in payload.history]

    def _generate() -> Iterator[str]:
        for chunk in stream_agent(payload.message, history=history):
            yield chunk

    return StreamingResponse(_generate(), media_type="text/plain; charset=utf-8")
