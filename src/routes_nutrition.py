"""
FastAPI router for nutrition data endpoints.
Provides /nutrition/search, /nutrition/filter, /nutrition/food/{name},
/nutrition/categories, and /nutrition/context endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.auth import _get_ready_app, _verify_api_key
from src.nutrition_retriever import NutritionEntry, get_nutrition_retriever


router = APIRouter(prefix="/nutrition", tags=["nutrition"])


class NutritionEntryResponse(BaseModel):
    name: str
    source: str
    category: str
    serving_size: str
    kcal_100g: float | None
    protein_100g: float | None
    carbs_100g: float | None
    fat_100g: float | None
    fiber_100g: float | None
    sugar_100g: float | None
    sodium_mg_100g: float | None
    is_high_protein: bool
    is_low_carb: bool


class NutritionSearchResponse(BaseModel):
    query: str
    count: int
    results: list[NutritionEntryResponse]


class NutritionFilterRequest(BaseModel):
    category: str | None = None
    high_protein: bool = False
    low_carb: bool = False
    low_fat: bool | None = None
    min_protein: float | None = None
    max_calories: float | None = None


class NutritionContextResponse(BaseModel):
    query: str
    context: str
    count: int


def _entry_to_response(entry: NutritionEntry) -> NutritionEntryResponse:
    return NutritionEntryResponse(
        name=entry.name,
        source=entry.source,
        category=entry.category,
        serving_size=entry.serving_size,
        kcal_100g=entry.kcal_100g,
        protein_100g=entry.protein_100g,
        carbs_100g=entry.carbs_100g,
        fat_100g=entry.fat_100g,
        fiber_100g=entry.fiber_100g,
        sugar_100g=entry.sugar_100g,
        sodium_mg_100g=entry.sodium_mg_100g,
        is_high_protein=entry.is_high_protein,
        is_low_carb=entry.is_low_carb,
    )


@router.get("/search", response_model=NutritionSearchResponse)
def search_nutrition(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results"),
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> NutritionSearchResponse:
    """Search nutrition database by keyword."""
    retriever = get_nutrition_retriever()
    results = retriever.search(q, top_k=top_k)
    return NutritionSearchResponse(
        query=q,
        count=len(results),
        results=[_entry_to_response(r) for r in results],
    )


@router.get("/food/{name}")
def get_food(
    name: str,
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> NutritionEntryResponse:
    """Get a specific food by name."""
    retriever = get_nutrition_retriever()
    entry = retriever.get_by_name(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Food not found: {name}")
    return _entry_to_response(entry)


@router.get("/filter", response_model=NutritionSearchResponse)
def filter_nutrition(
    category: str | None = None,
    high_protein: bool = False,
    low_carb: bool = False,
    low_fat: bool | None = None,
    min_protein: float | None = None,
    max_calories: float | None = None,
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> NutritionSearchResponse:
    """Filter nutrition database by structured criteria."""
    retriever = get_nutrition_retriever()
    results = retriever.filter(
        category=category,
        high_protein=high_protein,
        low_carb=low_carb,
        low_fat=low_fat,
        min_protein=min_protein,
        max_calories=max_calories,
    )
    return NutritionSearchResponse(
        query=f"filter(category={category}, high_protein={high_protein}, low_carb={low_carb})",
        count=len(results),
        results=[_entry_to_response(r) for r in results],
    )


@router.get("/categories")
def list_categories(
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> dict[str, list[str]]:
    """List all available nutrition categories."""
    retriever = get_nutrition_retriever()
    return {"categories": retriever.list_categories()}


@router.get("/context", response_model=NutritionContextResponse)
def get_nutrition_context(
    q: str = Query(..., min_length=1, max_length=200, description="Query to get context for"),
    top_k: int = Query(5, ge=1, le=20),
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> NutritionContextResponse:
    """Get LLM-injectable nutrition context for a query."""
    retriever = get_nutrition_retriever()
    results = retriever.search(q, top_k=top_k)
    context = retriever.format_for_llm(results)
    return NutritionContextResponse(query=q, context=context, count=len(results))
