"""
FastAPI router for exercise data endpoints.
Provides /exercises/search, /exercises/filter, /exercises/id/{id},
/exercises/options, and /exercises/context endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.auth import _get_ready_app, _verify_api_key
from src.exercise_retriever import ExerciseEntry, get_exercise_retriever


router = APIRouter(prefix="/exercises", tags=["exercises"])


class ExerciseResponse(BaseModel):
    id: str
    name: str
    force: str
    level: str
    mechanic: str
    equipment: str
    primaryMuscles: list[str]
    secondaryMuscles: list[str]
    instructions: list[str]
    category: str
    fitzone_domain: str
    images: list[str]


class ExerciseSearchResponse(BaseModel):
    query: str
    count: int
    results: list[ExerciseResponse]


class ExerciseContextResponse(BaseModel):
    query: str
    context: str
    count: int


class ExerciseOptionsResponse(BaseModel):
    categories: list[str]
    equipment: list[str]
    levels: list[str]
    muscles: list[str]
    total_exercises: int


def _entry_to_response(entry: ExerciseEntry) -> ExerciseResponse:
    return ExerciseResponse(
        id=entry.id,
        name=entry.name,
        force=entry.force,
        level=entry.level,
        mechanic=entry.mechanic,
        equipment=entry.equipment,
        primaryMuscles=entry.primary_muscles,
        secondaryMuscles=entry.secondary_muscles,
        instructions=entry.instructions,
        category=entry.category,
        fitzone_domain=entry.fitzone_domain,
        images=entry.images,
    )


@router.get("/search", response_model=ExerciseSearchResponse)
def search_exercises(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results"),
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> ExerciseSearchResponse:
    """Search exercises by keyword (name, muscle, equipment)."""
    retriever = get_exercise_retriever()
    results = retriever.search(q, top_k=top_k)
    return ExerciseSearchResponse(
        query=q,
        count=len(results),
        results=[_entry_to_response(r) for r in results],
    )


@router.get("/id/{exercise_id}")
def get_exercise_by_id(
    exercise_id: str,
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> ExerciseResponse:
    """Get a specific exercise by ID."""
    retriever = get_exercise_retriever()
    entry = retriever.get_by_id(exercise_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Exercise not found: {exercise_id}")
    return _entry_to_response(entry)


@router.get("/filter", response_model=ExerciseSearchResponse)
def filter_exercises(
    category: str | None = None,
    level: str | None = None,
    equipment: str | None = None,
    mechanic: str | None = None,
    primary_muscle: str | None = None,
    force: str | None = None,
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> ExerciseSearchResponse:
    """Filter exercises by structured criteria."""
    retriever = get_exercise_retriever()
    results = retriever.filter(
        category=category,
        level=level,
        equipment=equipment,
        mechanic=mechanic,
        primary_muscle=primary_muscle,
        force=force,
    )
    return ExerciseSearchResponse(
        query=f"filter(category={category}, equipment={equipment}, muscle={primary_muscle})",
        count=len(results),
        results=[_entry_to_response(r) for r in results],
    )


@router.get("/options", response_model=ExerciseOptionsResponse)
def get_options(
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> ExerciseOptionsResponse:
    """List all available filter options (categories, equipment, levels, muscles)."""
    retriever = get_exercise_retriever()
    return ExerciseOptionsResponse(
        categories=retriever.list_categories(),
        equipment=retriever.list_equipment(),
        levels=retriever.list_levels(),
        muscles=retriever.list_muscles(),
        total_exercises=retriever.count,
    )


@router.get("/context", response_model=ExerciseContextResponse)
def get_exercise_context(
    q: str = Query(..., min_length=1, max_length=200, description="Query to get context for"),
    top_k: int = Query(5, ge=1, le=20),
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> ExerciseContextResponse:
    """Get LLM-injectable exercise context for a query."""
    retriever = get_exercise_retriever()
    results = retriever.search(q, top_k=top_k)
    context = retriever.format_for_llm(results)
    return ExerciseContextResponse(query=q, context=context, count=len(results))
