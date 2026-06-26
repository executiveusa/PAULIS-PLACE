"""Council API - Convene multi-agent debates"""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from agents.council_agent import council_agent

router = APIRouter(prefix="/api/council", tags=["council"])


class ConveneRequest(BaseModel):
    topic: str
    problem_statement: str
    context: Optional[dict] = None


@router.post("/convene")
async def convene_council(req: ConveneRequest):
    """Convene the council to debate a problem"""
    result = await council_agent.convene(
        topic=req.topic,
        problem_statement=req.problem_statement,
        context=req.context
    )
    return result


@router.get("/deliberations")
def get_deliberations(limit: int = 10):
    """Get recent council deliberations"""
    return {
        "deliberations": council_agent.get_recent_deliberations(limit),
        "count": len(council_agent.get_recent_deliberations(limit))
    }
