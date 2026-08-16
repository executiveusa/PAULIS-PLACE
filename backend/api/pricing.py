from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Any

from services.pricing_market_gate import PricingGateBlocked, evaluate_pricing

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


class PricingEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str
    segment_id: str
    cogs: float = Field(ge=0)
    target_gross_margin: float = Field(ge=0, lt=1)
    proposed_price: float | None = Field(default=None, ge=0)
    recommended_price: float | None = Field(default=None, ge=0)
    evidence: dict[str, Any] = Field(default_factory=dict)
    purchases: dict[str, Any] = Field(default_factory=dict)


@router.post("/evaluate")
async def evaluate(body: PricingEvaluationRequest):
    try:
        return await evaluate_pricing(body.model_dump())
    except PricingGateBlocked as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
