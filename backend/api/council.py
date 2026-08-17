"""Council API - legacy debate plus Pauliverse portfolio council."""
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from agents.council_agent import council_agent
from agents.council_adversarial import debate as adversarial_debate
from agents.portfolio_council import deliberate as portfolio_deliberate, recent_deliberations

router = APIRouter(prefix="/api/council", tags=["council"])


class ConveneRequest(BaseModel):
    topic: str
    problem_statement: str
    context: Optional[dict] = None


class AdversarialDebateRequest(BaseModel):
    proposal: str
    context: str = ""


class PortfolioCouncilRequest(BaseModel):
    question: str
    proposal: str
    context: dict | str | None = None


@router.post("/convene")
async def convene_council(req: ConveneRequest):
    """Convene the legacy council."""
    return await council_agent.convene(
        topic=req.topic,
        problem_statement=req.problem_statement,
        context=req.context,
    )


@router.post("/debate")
async def convene_adversarial(req: AdversarialDebateRequest):
    """Run the strict 3-turn advocate/critic/judge debate."""
    return await adversarial_debate(proposal=req.proposal, context=req.context)


@router.post("/portfolio")
async def convene_portfolio_council(req: PortfolioCouncilRequest):
    """Run the seven-perspective Pauliverse council and Hermes synthesis.

    This endpoint performs model calls and persists a decision receipt. It does
    not itself execute the resulting commercial/destructive action; owner gates
    remain separate and server-authorized.
    """
    return await portfolio_deliberate(
        question=req.question,
        proposal=req.proposal,
        context=req.context,
    )


@router.get("/portfolio/deliberations")
def get_portfolio_deliberations(limit: int = Query(10, ge=1, le=100)):
    """Read persisted portfolio-council receipts for the Command World."""
    items = recent_deliberations(limit)
    return {"deliberations": items, "count": len(items)}


@router.get("/deliberations")
def get_deliberations(limit: int = 10):
    """Get recent legacy council deliberations."""
    items = council_agent.get_recent_deliberations(limit)
    return {"deliberations": items, "count": len(items)}
