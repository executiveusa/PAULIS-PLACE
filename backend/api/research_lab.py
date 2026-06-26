from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from models.base import get_db
from agents.autoresearch_agent import autoresearch_agent
from agents.idea_factory_agent import idea_factory
from services.wiki_service import wiki_service
from services.model_router import model_router

router = APIRouter(prefix="/api/research-lab", tags=["research_lab"])


class ResearchRequest(BaseModel):
    topic: str
    depth: str = "standard"  # "quick", "standard", "deep"
    context: Optional[dict] = None


class IdeaRequest(BaseModel):
    method: str  # "mashup", "etsy_autocomplete", "review_mine", "bundle", "pinterest"
    params: dict = {}


class WikiSearchRequest(BaseModel):
    query: str
    niche: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 10


@router.post("/research")
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Start AutoResearch on a topic"""
    if request.depth == "deep":
        raise HTTPException(400, "Deep research must be run as background task")

    result = await autoresearch_agent.research(
        topic=request.topic,
        context=request.context,
        depth=request.depth
    )

    # Add to wiki
    try:
        await wiki_service.add_from_research(result)
    except Exception as e:
        print(f"[Wiki] Add from research error: {e}")

    return {
        "status": "complete",
        "topic": result.topic,
        "confidence": result.confidence_score,
        "gaps_filled": result.gaps_filled,
        "searches_used": result.total_searches,
        "money_angles": result.money_angles,
        "next_actions": result.next_actions,
        "cost": model_router.get_cost_report()["total_cost"]
    }


@router.post("/ideas")
async def generate_ideas(request: IdeaRequest):
    """Generate ideas using specified method"""
    result = await idea_factory.generate_ideas(request.method, **request.params)

    return {
        "status": "complete",
        "method": request.method,
        "result": result,
        "cost": model_router.get_cost_report()["total_cost"]
    }


@router.post("/ideas/pipeline")
async def run_idea_pipeline(niche: str, background_tasks: BackgroundTasks):
    """Run full idea generation pipeline for a niche"""
    background_tasks.add_task(run_pipeline_background, niche)

    return {
        "status": "queued",
        "niche": niche,
        "message": "Full pipeline running in background"
    }


async def run_pipeline_background(niche: str):
    """Background pipeline execution"""
    try:
        result = await idea_factory.run_full_idea_pipeline(niche)
        print(f"[Pipeline] Complete for {niche}: {len(result.get('methods', {}))} methods run")
    except Exception as e:
        print(f"[Pipeline] Error for {niche}: {e}")


@router.post("/wiki/search")
async def search_wiki(request: WikiSearchRequest, db: Session = Depends(get_db)):
    """Search the LLM Wiki"""
    results = wiki_service.search(
        query=request.query,
        niche=request.niche,
        category=request.category,
        tags=request.tags,
        limit=request.limit
    )

    return {
        "query": request.query,
        "results": [
            {
                "entry": r.entry.to_dict(),
                "relevance": r.relevance_score,
                "match_type": r.match_type
            }
            for r in results
        ],
        "count": len(results)
    }


@router.get("/wiki/stats")
async def get_wiki_stats():
    """Get wiki statistics"""
    return wiki_service.get_stats()


@router.get("/costs")
async def get_cost_report():
    """Get detailed cost breakdown"""
    return model_router.get_cost_report()


@router.get("/model-usage")
async def get_model_usage():
    """Get model usage patterns"""
    report = model_router.get_cost_report()

    return {
        "total_cost": report["total_cost"],
        "call_count": report["call_count"],
        "avg_cost_per_call": report["avg_cost_per_call"],
        "by_model": {
            name: {
                "cost": cost,
                "percentage": (cost / report["total_cost"] * 100) if report["total_cost"] > 0 else 0
            }
            for name, cost in report["by_model"].items()
        },
        "efficiency_score": _calculate_efficiency(report)
    }


@router.get("/logs")
async def get_recent_logs(limit: int = 50):
    """Get recent model usage logs for the observation console"""
    return {
        "logs": model_router.get_recent_logs(limit),
        "count": len(model_router.get_recent_logs(limit))
    }


def _calculate_efficiency(report: dict) -> float:
    """Calculate how efficiently we're using models"""
    if report["total_cost"] == 0:
        return 1.0

    target_cost_per_call = 0.002
    actual_cost_per_call = report["avg_cost_per_call"]

    return min(1.0, target_cost_per_call / max(actual_cost_per_call, 0.0001))
