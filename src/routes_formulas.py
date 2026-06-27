"""
FastAPI router for formula calculation endpoints.
Provides /formulas/list, /formulas/calculate, /formulas/search, and /formulas/info endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.auth import _get_ready_app, _verify_api_key
from src.formula_calculator import get_formula_calculator


router = APIRouter(prefix="/formulas", tags=["formulas"])


class FormulaInfoResponse(BaseModel):
    id: str
    name: str
    category: str
    description: str
    formula: str
    inputs: list[dict]
    conditions: str
    alternatives: list[str]


class FormulaCalcRequest(BaseModel):
    formula_id: str
    inputs: dict[str, float | str]


class FormulaCalcResponse(BaseModel):
    formula_name: str
    formula_id: str
    inputs: dict
    result: float | dict | None
    unit: str
    explanation: str
    science_mode_output: str


@router.get("/list")
def list_formulas(
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> dict:
    """List all available formulas."""
    calc = get_formula_calculator()
    return {"formulas": calc.list_formulas(), "count": len(calc.list_formulas())}


@router.get("/search")
def search_formulas(
    q: str = Query(..., min_length=1, max_length=100),
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> dict:
    """Search formulas by keyword."""
    calc = get_formula_calculator()
    results = calc.search(q)
    return {"query": q, "results": results, "count": len(results)}


@router.get("/info/{formula_id}")
def get_formula_info(
    formula_id: str,
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> FormulaInfoResponse:
    """Get detailed info about a specific formula."""
    calc = get_formula_calculator()
    info = calc.get_formula_info(formula_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Formula not found: {formula_id}")
    return FormulaInfoResponse(
        id=formula_id,
        name=info["name"],
        category=info["category"],
        description=info["description"],
        formula=info["formula"],
        inputs=info["inputs"],
        conditions=info["conditions"],
        alternatives=info.get("alternatives", []),
    )


@router.post("/calculate", response_model=FormulaCalcResponse)
def calculate_formula(
    request: FormulaCalcRequest,
    _: None = Depends(_verify_api_key),
    _app=Depends(_get_ready_app),
) -> FormulaCalcResponse:
    """Calculate a formula result."""
    calc = get_formula_calculator()
    result = calc.calculate(request.formula_id, **request.inputs)
    if result is None:
        raise HTTPException(
            status_code=400,
            detail=f"Could not calculate {request.formula_id} with given inputs: {request.inputs}",
        )
    return FormulaCalcResponse(
        formula_name=result.formula_name,
        formula_id=result.formula_id,
        inputs=result.inputs,
        result=result.result,
        unit=result.unit,
        explanation=result.explanation,
        science_mode_output=result.to_science_mode_string(),
    )
