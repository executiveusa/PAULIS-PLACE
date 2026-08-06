"""Council API - Convene multi-agent debates"""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from agents.council_agent import council_agent
<<<<<<< HEAD
from agents.council_adversarial import debate as adversarial_debate
=======
>>>>>>> origin/main

router = APIRouter(prefix="/api/council", tags=["council"])


class ConveneRequest(BaseModel):
    topic: str
    problem_statement: str
    context: Optional[dict] = None


<<<<<<< HEAD
class AdversarialDebateRequest(BaseModel):
    proposal: str
    context: str = ""


@router.post("/convene")
async def convene_council(req: ConveneRequest):
    """Convene the (legacy 4-turn) council to debate a problem"""
=======
@router.post("/convene")
async def convene_council(req: ConveneRequest):
    """Convene the council to debate a problem"""
>>>>>>> origin/main
    result = await council_agent.convene(
        topic=req.topic,
        problem_statement=req.problem_statement,
        context=req.context
    )
    return result


<<<<<<< HEAD
@router.post("/debate")
async def convene_adversarial(req: AdversarialDebateRequest):
    """Spec §02 — strict 3-turn adversarial debate (advocate/critic/judge)
    Returns the locked ruling + debate_id."""
    return await adversarial_debate(proposal=req.proposal, context=req.context)


=======
>>>>>>> origin/main
@router.get("/deliberations")
def get_deliberations(limit: int = 10):
    """Get recent council deliberations"""
    return {
        "deliberations": council_agent.get_recent_deliberations(limit),
        "count": len(council_agent.get_recent_deliberations(limit))
    }
