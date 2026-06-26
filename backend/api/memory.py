"""Memory System API - Evolving memory stats and management"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from models.base import get_db
from services.evolving_memory import evolving_memory, EvolvingMemory, MemoryType

router = APIRouter(prefix="/api/memory", tags=["memory"])


class ScaffoldCreateRequest(BaseModel):
    name: str
    purpose: str
    steps: List[dict]
    preconditions: List[str]
    success_criteria: List[str]
    tags: List[str]


@router.get("/stats")
async def get_memory_stats():
    """Get evolving memory system statistics"""
    return evolving_memory.get_memory_stats()


@router.get("/anti-patterns")
async def get_anti_patterns(limit: int = 10):
    """Get active anti-patterns"""
    return {
        "anti_patterns": evolving_memory.get_anti_patterns(limit),
        "count": len(evolving_memory.get_anti_patterns(limit))
    }


@router.get("/search")
async def search_memories(
    context: str,
    memory_types: Optional[str] = None,
    limit: int = 10
):
    """Search for relevant memories"""
    types = None
    if memory_types:
        types = [MemoryType(t) for t in memory_types.split(",")]

    memories = await evolving_memory.get_relevant_memories(
        context=context,
        memory_types=types,
        limit=limit
    )
    return {"memories": memories, "count": len(memories)}


@router.post("/scaffold")
async def create_scaffold(req: ScaffoldCreateRequest):
    """Create a new scaffold (reusable strategy)"""
    scaffold_id = await evolving_memory.create_scaffold(
        name=req.name,
        purpose=req.purpose,
        steps=req.steps,
        preconditions=req.preconditions,
        success_criteria=req.success_criteria,
        tags=req.tags
    )
    return {"scaffold_id": scaffold_id, "status": "created"}


@router.get("/scaffolds")
async def get_scaffolds(task_type: Optional[str] = None):
    """Get scaffolds, optionally filtered by task type"""
    if task_type:
        scaffold = await evolving_memory.get_scaffold_for_task(task_type)
        return {"scaffold": scaffold, "found": scaffold is not None}
    else:
        # Return all scaffolds
        from models.base import SessionLocal
        db = SessionLocal()
        try:
            scaffolds = db.query(EvolvingMemory).filter(
                EvolvingMemory.memory_type == MemoryType.SCAFFOLD.value,
                EvolvingMemory.is_active == True
            ).all()
            return {
                "scaffolds": [s.to_dict() for s in scaffolds],
                "count": len(scaffolds)
            }
        finally:
            db.close()
