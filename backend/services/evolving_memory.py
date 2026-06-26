"""
SELF-EVOLVING MEMORY SYSTEM
============================
Inspired by Ornith-1.0's RL scaffolds, applied to the ENTIRE system.

The system learns its own optimal strategies through:
1. Execution tracking (what worked, what didn't)
2. Pattern extraction (common success/failure modes)
3. Scaffold generation (creating reusable strategies)
4. Self-modification (updating its own prompts/processes)
5. Meta-learning (learning HOW to learn better)
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, Boolean, Index, func
from models.base import Base, SessionLocal
from services.model_router import model_router


class MemoryType(str, Enum):
    EXECUTION_LOG = "execution_log"
    PATTERN = "pattern"
    SCAFFOLD = "scaffold"
    ANTI_PATTERN = "anti_pattern"
    META_LEARNING = "meta_learning"
    SELF_MODIFICATION = "self_modification"


class ConfidenceLevel(str, Enum):
    HYPOTHESIS = "hypothesis"
    EMERGING = "emerging"
    VALIDATED = "validated"
    CANONICAL = "canonical"


@dataclass
class MemoryNode:
    id: str
    type: MemoryType
    content: Dict[str, Any]
    confidence: ConfidenceLevel
    evidence_count: int
    success_rate: float
    created_at: datetime
    evolved_at: datetime
    parent_nodes: List[str] = field(default_factory=list)
    child_nodes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    times_used: int = 0
    times_succeeded: int = 0


class EvolvingMemory(Base):
    __tablename__ = "evolving_memory"

    id = Column(Integer, primary_key=True, index=True)
    memory_id = Column(String(100), unique=True, index=True)
    memory_type = Column(String(50), index=True)
    content = Column(JSON, nullable=False)
    confidence = Column(String(20), default="hypothesis")
    evidence_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    parent_ids = Column(JSON, default=list)
    child_ids = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    times_used = Column(Integer, default=0)
    times_succeeded = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    evolved_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scaffold_steps = Column(JSON, nullable=True)
    preconditions = Column(JSON, default=list)
    success_criteria = Column(JSON, default=list)

    target_file = Column(String(500), nullable=True)
    modification_type = Column(String(50), nullable=True)
    rollback_content = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "memory_id": self.memory_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "success_rate": self.success_rate,
            "tags": self.tags or [],
            "times_used": self.times_used,
            "times_succeeded": self.times_succeeded,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "evolved_at": self.evolved_at.isoformat() if self.evolved_at else None,
        }


class EvolvingMemorySystem:
    """The core self-evolving memory system."""

    def __init__(self):
        self.db = SessionLocal()
        self.evolution_threshold = 3
        self.demotion_threshold = 0.3

    async def log_execution(
        self,
        agent: str,
        task_type: str,
        input_context: Dict,
        output_result: Dict,
        success: bool,
        duration_seconds: float,
        cost: float,
        memories_used: List[str] = None
    ) -> str:
        """Log an execution and update all related memories"""
        memory_id = self._generate_id(f"exec_{agent}_{task_type}")

        execution_memory = EvolvingMemory(
            memory_id=memory_id,
            memory_type=MemoryType.EXECUTION_LOG.value,
            content={
                "agent": agent,
                "task_type": task_type,
                "input": self._hash_sensitive(input_context),
                "output_summary": self._summarize_output(output_result),
                "success": success,
                "duration_seconds": duration_seconds,
                "cost": cost,
                "timestamp": datetime.utcnow().isoformat()
            },
            confidence=ConfidenceLevel.CANONICAL.value,
            evidence_count=1,
            tags=[agent, task_type, "execution"]
        )

        self.db.add(execution_memory)

        if memories_used:
            for mem_id in memories_used:
                await self._update_memory_usage(mem_id, success)

        await self._extract_patterns(execution_memory)

        self.db.commit()
        return memory_id

    async def _update_memory_usage(self, memory_id: str, success: bool):
        memory = self.db.query(EvolvingMemory).filter(
            EvolvingMemory.memory_id == memory_id
        ).first()

        if not memory:
            return

        memory.times_used += 1
        if success:
            memory.times_succeeded += 1

        if memory.times_used > 0:
            memory.success_rate = memory.times_succeeded / memory.times_used

        await self._evolve_confidence(memory)

        if memory.memory_type == MemoryType.SCAFFOLD.value:
            await self._refine_scaffold(memory)

    async def _evolve_confidence(self, memory: EvolvingMemory):
        old_confidence = memory.confidence
        new_confidence = old_confidence

        if memory.confidence == ConfidenceLevel.HYPOTHESIS.value:
            if memory.evidence_count >= 3 and memory.success_rate >= 0.6:
                new_confidence = ConfidenceLevel.EMERGING.value
        elif memory.confidence == ConfidenceLevel.EMERGING.value:
            if memory.evidence_count >= 10 and memory.success_rate >= 0.7:
                new_confidence = ConfidenceLevel.VALIDATED.value
        elif memory.confidence == ConfidenceLevel.VALIDATED.value:
            if memory.evidence_count >= 50 and memory.success_rate >= 0.85:
                new_confidence = ConfidenceLevel.CANONICAL.value

        if memory.times_used >= 10 and memory.success_rate < self.demotion_threshold:
            if memory.confidence == ConfidenceLevel.CANONICAL.value:
                new_confidence = ConfidenceLevel.VALIDATED.value
            elif memory.confidence == ConfidenceLevel.VALIDATED.value:
                new_confidence = ConfidenceLevel.EMERGING.value
            elif memory.confidence == ConfidenceLevel.EMERGING.value:
                new_confidence = ConfidenceLevel.HYPOTHESIS.value
                memory.is_active = False

        memory.confidence = new_confidence
        memory.evolved_at = datetime.utcnow()

        if old_confidence != new_confidence:
            await self._log_meta_learning(
                f"Memory {memory.memory_id} evolved from {old_confidence} to {new_confidence}",
                {
                    "old_confidence": old_confidence,
                    "new_confidence": new_confidence,
                    "evidence_count": memory.evidence_count,
                    "success_rate": memory.success_rate
                }
            )

    async def _extract_patterns(self, execution: EvolvingMemory):
        recent = self.db.query(EvolvingMemory).filter(
            EvolvingMemory.memory_type == MemoryType.EXECUTION_LOG.value,
            EvolvingMemory.id != execution.id
        ).order_by(EvolvingMemory.created_at.desc()).limit(10).all()

        if len(recent) < 3:
            return

        executions_summary = [
            {
                "success": e.content.get("success", False),
                "output": e.content.get("output_summary", ""),
                "cost": e.content.get("cost", 0)
            }
            for e in recent
        ]

        try:
            pattern_extraction = await model_router.call(
                "extract_memory_patterns",
                f"""Analyze these {len(recent)} executions and extract patterns:

Agent: {execution.content.get("agent", "unknown")}
Task: {execution.content.get("task_type", "unknown")}
Executions: {json.dumps(executions_summary, indent=2)}

Find:
1. SUCCESS PATTERNS: What do successful executions have in common?
2. FAILURE PATTERNS: What do failed executions have in common?
3. EFFICIENCY PATTERNS: Which executions had best cost-to-success ratio?

Output JSON:
{{
    "success_patterns": [{{"pattern": "description", "confidence": 0.8}}],
    "failure_patterns": [{{"pattern": "description", "confidence": 0.8}}],
    "efficiency_patterns": [{{"pattern": "description", "confidence": 0.8}}]
}}""",
                system_prompt="You extract patterns from execution data. Be specific and actionable.",
                force_model="llama-8b",
                temperature=0.3
            )

            patterns = pattern_extraction["content"]
            if isinstance(patterns, str):
                patterns = json.loads(patterns)

            for pattern in patterns.get("success_patterns", []):
                await self._store_pattern(
                    pattern.get("pattern", ""),
                    MemoryType.PATTERN,
                    pattern.get("confidence", 0.5),
                    [execution.content.get("agent", ""), execution.content.get("task_type", ""), "success"]
                )

            for pattern in patterns.get("failure_patterns", []):
                await self._store_pattern(
                    pattern.get("pattern", ""),
                    MemoryType.ANTI_PATTERN,
                    pattern.get("confidence", 0.5),
                    [execution.content.get("agent", ""), execution.content.get("task_type", ""), "failure"]
                )
        except Exception as e:
            print(f"[Memory] Pattern extraction error: {e}")

    async def _store_pattern(
        self,
        pattern_text: str,
        pattern_type: MemoryType,
        confidence: float,
        tags: List[str]
    ):
        if not pattern_text:
            return

        existing = self.db.query(EvolvingMemory).filter(
            EvolvingMemory.memory_type == pattern_type.value,
        ).first()

        if existing:
            existing.evidence_count += 1
            existing.evolved_at = datetime.utcnow()
            return

        pattern_id = self._generate_id(f"{pattern_type.value}_{hashlib.md5(pattern_text.encode()).hexdigest()[:8]}")

        pattern_memory = EvolvingMemory(
            memory_id=pattern_id,
            memory_type=pattern_type.value,
            content={"pattern": pattern_text},
            confidence=ConfidenceLevel.HYPOTHESIS.value,
            evidence_count=1,
            success_rate=confidence,
            tags=[t for t in tags if t]
        )

        self.db.add(pattern_memory)

    async def create_scaffold(
        self,
        name: str,
        purpose: str,
        steps: List[Dict],
        preconditions: List[str],
        success_criteria: List[str],
        tags: List[str]
    ) -> str:
        scaffold_id = self._generate_id(f"scaffold_{name}")

        scaffold = EvolvingMemory(
            memory_id=scaffold_id,
            memory_type=MemoryType.SCAFFOLD.value,
            content={
                "name": name,
                "purpose": purpose,
                "created_from": "manual"
            },
            confidence=ConfidenceLevel.HYPOTHESIS.value,
            scaffold_steps=steps,
            preconditions=preconditions,
            success_criteria=success_criteria,
            tags=tags + ["scaffold"]
        )

        self.db.add(scaffold)
        self.db.commit()

        return scaffold_id

    async def get_scaffold_for_task(self, task_type: str) -> Optional[Dict]:
        scaffolds = self.db.query(EvolvingMemory).filter(
            EvolvingMemory.memory_type == MemoryType.SCAFFOLD.value,
            EvolvingMemory.is_active == True
        ).order_by(
            EvolvingMemory.success_rate.desc(),
            EvolvingMemory.times_used.desc()
        ).limit(3).all()

        if not scaffolds:
            return None

        best = scaffolds[0]
        return {
            "scaffold_id": best.memory_id,
            "name": best.content.get("name"),
            "steps": best.scaffold_steps,
            "preconditions": best.preconditions,
            "success_criteria": best.success_criteria,
            "confidence": best.confidence,
            "success_rate": best.success_rate,
            "times_used": best.times_used
        }

    async def _refine_scaffold(self, scaffold: EvolvingMemory):
        if scaffold.times_used < 5:
            return

        try:
            step_analysis = await model_router.call(
                "analyze_scaffold_steps",
                f"""Analyze this scaffold's performance:

Scaffold: {scaffold.content.get("name")}
Steps: {json.dumps(scaffold.scaffold_steps or [], indent=2)}
Recent Success Rate: {scaffold.success_rate}

Identify which steps are causing failures and suggest fixes.
Output JSON:
{{
    "step_analysis": [
        {{"step_index": 0, "issue": "what's wrong", "suggested_fix": "how to fix", "priority": "high"}}
    ],
    "overall_assessment": "brief assessment"
}}""",
                system_prompt="You analyze scaffold performance and suggest improvements.",
                force_model="llama-8b",
                temperature=0.3
            )

            analysis = step_analysis["content"]
            if isinstance(analysis, str):
                analysis = json.loads(analysis)

            for step in analysis.get("step_analysis", []):
                if step.get("priority") == "high":
                    idx = step.get("step_index", 0)
                    if scaffold.scaffold_steps and idx < len(scaffold.scaffold_steps):
                        scaffold.scaffold_steps[idx]["description"] = step.get("suggested_fix", "")
                        scaffold.scaffold_steps[idx]["refined_at"] = datetime.utcnow().isoformat()

            scaffold.evolved_at = datetime.utcnow()
        except Exception as e:
            print(f"[Memory] Scaffold refinement error: {e}")

    async def propose_self_modification(
        self,
        target_file: str,
        modification_type: str,
        current_content: str,
        reason: str,
        proposed_change: str
    ) -> str:
        mod_id = self._generate_id(f"selfmod_{target_file}_{modification_type}")

        modification = EvolvingMemory(
            memory_id=mod_id,
            memory_type=MemoryType.SELF_MODIFICATION.value,
            content={
                "target_file": target_file,
                "modification_type": modification_type,
                "reason": reason,
                "proposed_change": proposed_change
            },
            confidence=ConfidenceLevel.HYPOTHESIS.value,
            target_file=target_file,
            modification_type=modification_type,
            rollback_content={"original": current_content},
            tags=["self_modification", target_file, modification_type]
        )

        self.db.add(modification)
        self.db.commit()

        return mod_id

    async def get_relevant_memories(
        self,
        context: str,
        memory_types: List[MemoryType] = None,
        min_confidence: ConfidenceLevel = ConfidenceLevel.EMERGING,
        limit: int = 10
    ) -> List[Dict]:
        if memory_types is None:
            memory_types = [MemoryType.PATTERN, MemoryType.SCAFFOLD]

        type_values = [t.value for t in memory_types]
        conf_order = ["hypothesis", "emerging", "validated", "canonical"]
        min_idx = conf_order.index(min_confidence.value) if min_confidence.value in conf_order else 1
        conf_values = conf_order[min_idx:]

        memories = self.db.query(EvolvingMemory).filter(
            EvolvingMemory.memory_type.in_(type_values),
            EvolvingMemory.confidence.in_(conf_values),
            EvolvingMemory.is_active == True
        ).order_by(
            EvolvingMemory.success_rate.desc(),
            EvolvingMemory.times_used.desc()
        ).limit(limit * 2).all()

        context_words = set(context.lower().split())
        relevant = []

        for memory in memories:
            memory_text = json.dumps(memory.content, default=str).lower()
            memory_words = set(memory_text.split())
            relevance = len(context_words & memory_words) / max(len(context_words), 1)

            if relevance > 0.1:
                relevant.append({
                    "memory_id": memory.memory_id,
                    "type": memory.memory_type,
                    "content": memory.content,
                    "confidence": memory.confidence,
                    "success_rate": memory.success_rate,
                    "relevance": relevance,
                    "times_used": memory.times_used
                })

        relevant.sort(key=lambda x: x["relevance"] * max(x["success_rate"], 0.1), reverse=True)

        return relevant[:limit]

    async def _log_meta_learning(self, insight: str, context: Dict):
        meta_id = self._generate_id(f"meta_{hashlib.md5(insight.encode()).hexdigest()[:8]}")

        meta = EvolvingMemory(
            memory_id=meta_id,
            memory_type=MemoryType.META_LEARNING.value,
            content={
                "insight": insight,
                "context": context
            },
            confidence=ConfidenceLevel.VALIDATED.value,
            tags=["meta_learning"]
        )

        self.db.add(meta)

    def _generate_id(self, prefix: str) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        hash_part = hashlib.md5(f"{prefix}{timestamp}".encode()).hexdigest()[:8]
        return f"{prefix}_{timestamp}_{hash_part}"

    def _hash_sensitive(self, data: Dict) -> str:
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def _summarize_output(self, output: Dict) -> str:
        if isinstance(output, dict):
            if "title" in output:
                return str(output["title"])[:100]
            if "content" in output:
                return str(output["content"])[:100]
        return str(output)[:100]

    def get_memory_stats(self) -> Dict:
        return {
            "total_memories": self.db.query(func.count(EvolvingMemory.id)).scalar() or 0,
            "by_type": dict(
                self.db.query(EvolvingMemory.memory_type, func.count(EvolvingMemory.id))
                .group_by(EvolvingMemory.memory_type).all()
            ),
            "by_confidence": dict(
                self.db.query(EvolvingMemory.confidence, func.count(EvolvingMemory.id))
                .group_by(EvolvingMemory.confidence).all()
            ),
            "avg_success_rate": float(self.db.query(func.avg(EvolvingMemory.success_rate)).scalar() or 0),
            "total_uses": self.db.query(func.sum(EvolvingMemory.times_used)).scalar() or 0,
            "self_modifications_pending": self.db.query(func.count(EvolvingMemory.id))
                .filter(EvolvingMemory.memory_type == MemoryType.SELF_MODIFICATION.value).scalar() or 0,
        }

    def get_anti_patterns(self, limit: int = 10) -> List[Dict]:
        """Get active anti-patterns for the master prompt"""
        conf_values = ["emerging", "validated", "canonical"]
        anti_patterns = self.db.query(EvolvingMemory).filter(
            EvolvingMemory.memory_type == MemoryType.ANTI_PATTERN.value,
            EvolvingMemory.confidence.in_(conf_values),
            EvolvingMemory.is_active == True
        ).order_by(EvolvingMemory.success_rate.desc()).limit(limit).all()

        return [
            {
                "pattern": ap.content.get("pattern", "Unknown"),
                "confidence": ap.confidence
            }
            for ap in anti_patterns
        ]


evolving_memory = EvolvingMemorySystem()
