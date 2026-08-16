from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import Any

from services.pricing_market_gate import PricingGateBlocked, evaluate_pricing

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


class PricingEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    product_id: str
    segment_id: str
    proposed_price: float | None = None
    evidence: dict[str, Any] = {}


@router.post("/evaluate")
async def evaluate(body: PricingEvaluationRequest):
    try:
        return await evaluate_pricing(body.model_dump())
    except PricingGateBlocked as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
