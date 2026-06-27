"""
Shared authentication dependencies for FitZone API routers.
Extracted from api.py to avoid circular imports.
"""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException, status

from src.config import GROQ_API_KEY


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


def _get_ready_app() -> FastAPI:
    """Dependency that returns the app and verifies readiness."""
    from src.api import app

    if not getattr(app.state, "ready", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=getattr(app.state, "startup_error", "Service is not ready."),
        )
    return app
