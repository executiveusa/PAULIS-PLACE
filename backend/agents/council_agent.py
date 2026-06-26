"""
THE COUNCIL - Multi-Agent Reasoning
====================================
Inspired by Karpathy's llm-council.

When a hard problem arises (product failure, cost-limit, trend contradiction),
spin up 3 agents who debate via Redis Pub/Sub:
- GLM-5.2 as Judge (final ruling)
- DeepSeek as Advocate (proposes path forward)
- Ornith-1 as Devil's Advocate (finds flaws, cheaper alternatives)

Output: A locked council_decision record in DB that Celery executes.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Float
from models.base import Base, SessionLocal
from services.model_router import model_router
from prompts.ruthless_system import RUTHLESS_SYSTEM_PROMPT
from config import SETTINGS


class CouncilTopic(str, Enum):
    PRODUCT_FAILED_QA = "product_failed_qa"
    COST_LIMIT_WARNING = "cost_limit_warning"
    TREND_CONTRADICTION = "trend_contradiction"
    LOW_PERFORMING_PRODUCT = "low_performing_product"
    STRATEGIC_PIVOT = "strategic_pivot"


class CouncilStatus(str, Enum):
    DELIBERATING = "deliberating"
    DECIDED = "decided"
    EXECUTED = "executed"
    FAILED = "failed"


class CouncilDeliberation(Base):
    """Immutable ledger of council debates and decisions"""
    __tablename__ = "council_deliberations"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(100), index=True)
    status = Column(String(50), default=CouncilStatus.DELIBERATING.value)

    # The problem
    problem_statement = Column(Text, nullable=False)
    context = Column(JSON, default=dict)

    # The debate (array of turns)
    debate_log = Column(JSON, default=list)

    # Final decision
    decision = Column(JSON, nullable=True)
    ruling = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)

    # Execution
    executed_at = Column(DateTime, nullable=True)
    execution_result = Column(JSON, nullable=True)

    # Cost tracking
    total_cost = Column(Float, default=0.0)
    turns = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "topic": self.topic,
            "status": self.status,
            "problem_statement": self.problem_statement,
            "context": self.context,
            "debate_log": self.debate_log,
            "decision": self.decision,
            "ruling": self.ruling,
            "rationale": self.rationale,
            "total_cost": self.total_cost,
            "turns": self.turns,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class CouncilTurn:
    """A single turn in the debate"""
    agent: str  # "advocate", "critic", "judge"
    model: str
    content: str
    cost: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class CouncilAgent:
    """
    The Council Protocol:
    1. Advocate (DeepSeek): Proposes a path forward based on data
    2. Critic (Ornith-1): Attempts to find flaws, edge cases, cheaper alternatives
    3. Judge (GLM-5.2): Makes the final ruling based on RUTHLESS metrics

    They debate for 3 turns. Output is a locked decision.
    """

    def __init__(self, max_turns: int = 3):
        self.max_turns = max_turns

    async def convene(
        self,
        topic: str,
        problem_statement: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """Convene the council to debate a problem"""
        context = context or {}
        db = SessionLocal()

        # Create deliberation record
        deliberation = CouncilDeliberation(
            topic=topic,
            problem_statement=problem_statement,
            context=context,
            debate_log=[],
            status=CouncilStatus.DELIBERATING.value
        )
        db.add(deliberation)
        db.commit()
        db.refresh(deliberation)

        debate_log: List[Dict] = []
        total_cost = 0.0

        try:
            # Turn 1: Advocate proposes
            advocate_turn = await self._advocate_turn(
                problem_statement, context, previous_turns=[]
            )
            debate_log.append(advocate_turn)
            total_cost += advocate_turn["cost"]

            # Turn 2: Critic attacks
            critic_turn = await self._critic_turn(
                problem_statement, context, advocate_proposal=advocate_turn["content"],
                previous_turns=[advocate_turn]
            )
            debate_log.append(critic_turn)
            total_cost += critic_turn["cost"]

            # Turn 3: Advocate defends / refines
            advocate_turn_2 = await self._advocate_turn(
                problem_statement, context,
                previous_turns=[advocate_turn, critic_turn],
                is_defense=True
            )
            debate_log.append(advocate_turn_2)
            total_cost += advocate_turn_2["cost"]

            # Final ruling from the Judge
            judge_turn = await self._judge_turn(
                problem_statement, context, debate_log
            )
            debate_log.append(judge_turn)
            total_cost += judge_turn["cost"]

            # Lock the decision
            decision = judge_turn["content"] if isinstance(judge_turn["content"], dict) else {
                "ruling": str(judge_turn["content"]),
                "action": "manual_review"
            }

            deliberation.debate_log = debate_log
            deliberation.decision = decision
            deliberation.ruling = decision.get("ruling", "no_ruling")
            deliberation.rationale = decision.get("rationale", "")
            deliberation.total_cost = total_cost
            deliberation.turns = len(debate_log)
            deliberation.status = CouncilStatus.DECIDED.value
            deliberation.completed_at = datetime.utcnow()

            db.commit()
            db.refresh(deliberation)

            return deliberation.to_dict()

        except Exception as e:
            deliberation.status = CouncilStatus.FAILED.value
            deliberation.rationale = f"Council error: {e}"
            deliberation.debate_log = debate_log
            deliberation.total_cost = total_cost
            db.commit()
            raise
        finally:
            db.close()

    async def _advocate_turn(
        self,
        problem: str,
        context: Dict,
        previous_turns: List[Dict],
        is_defense: bool = False
    ) -> Dict:
        """The Advocate (DeepSeek) proposes or defends a path forward"""
        prev_summary = json.dumps(previous_turns, indent=2) if previous_turns else "None"

        if is_defense:
            prompt = f"""You are the ADVOCATE in a council debate. The Critic has attacked your proposal. Defend or refine it.

PROBLEM: {problem}
CONTEXT: {context}

PREVIOUS TURNS:
{prev_summary}

Respond to the Critic's attacks. Either:
1. Defend your position with evidence, OR
2. Refine your proposal to address valid concerns, OR
3. Concede if the Critic found a fatal flaw

Output JSON:
{{
    "position": "defended" | "refined" | "conceded",
    "refined_proposal": "your updated proposal (if refined)",
    "defense": "why your proposal still stands",
    "concession": "what you concede (if anything)"
}}"""
        else:
            prompt = f"""You are the ADVOCATE in a council debate. Propose the best path forward.

PROBLEM: {problem}
CONTEXT: {context}

Based on the RUTHLESS framework, propose:
1. The specific action to take
2. Why this is the best path
3. Expected outcome (money metrics)
4. Risks and mitigations

Output JSON:
{{
    "proposal": "specific action to take",
    "rationale": "why this is best",
    "expected_revenue": 0.00,
    "expected_cost": 0.00,
    "risks": ["risk 1", "risk 2"],
    "mitigations": ["mitigation 1", "mitigation 2"]
}}"""

        result = await model_router.call(
            "council_advocate",
            prompt,
            system_prompt=RUTHLESS_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
            force_model="deepseek-v2",
            temperature=0.6
        )

        content = result["content"] if isinstance(result["content"], dict) else {"proposal": str(result["content"])}
        cost = result["usage"]["cost"]

        return {
            "agent": "advocate",
            "model": "DeepSeek-V2",
            "content": content,
            "cost": cost,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _critic_turn(
        self,
        problem: str,
        context: Dict,
        advocate_proposal: Dict,
        previous_turns: List[Dict]
    ) -> Dict:
        """The Critic (Ornith-1) attacks the proposal"""
        prompt = f"""You are the CRITIC (Devil's Advocate) in a council debate. Find every flaw in the Advocate's proposal.

PROBLEM: {problem}
CONTEXT: {context}

ADVOCATE'S PROPOSAL:
{json.dumps(advocate_proposal, indent=2)}

Attack the proposal on:
1. Logical flaws
2. Missing edge cases
3. Cheaper alternatives that achieve the same goal
4. Hidden costs or risks
5. Whether this actually makes money

Be brutal. If the proposal is sound, say so. If not, destroy it.

Output JSON:
{{
    "verdict": "sound" | "flawed" | "fatal_flaw",
    "flaws": ["flaw 1", "flaw 2"],
    "cheaper_alternative": "a cheaper way to achieve the same goal (if any)",
    "missing_considerations": ["thing 1", "thing 2"],
    "recommendation": "proceed" | "revise" | "abandon"
}}"""

        result = await model_router.call(
            "council_critic",
            prompt,
            system_prompt="You are a ruthless critic. Find flaws. Be specific. No hand-waving.",
            response_format={"type": "json_object"},
            force_model="ornith-1",
            temperature=0.4
        )

        content = result["content"] if isinstance(result["content"], dict) else {"verdict": str(result["content"])}
        cost = result["usage"]["cost"]

        return {
            "agent": "critic",
            "model": "Ornith-1",
            "content": content,
            "cost": cost,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _judge_turn(
        self,
        problem: str,
        context: Dict,
        debate_log: List[Dict]
    ) -> Dict:
        """The Judge (GLM-5.2) makes the final ruling"""
        prompt = f"""You are the JUDGE in a council debate. Make the final ruling.

PROBLEM: {problem}
CONTEXT: {context}

FULL DEBATE:
{json.dumps(debate_log, indent=2)}

Based on the RUTHLESS framework, make a final ruling:
1. What is the decided action?
2. Why (synthesizing the debate)?
3. What are the success criteria?
4. What is the rollback plan if this fails?

Your ruling is FINAL and will be executed automatically by the system.

Output JSON:
{{
    "ruling": "execute_proposal" | "execute_revised" | "execute_alternative" | "abandon" | "manual_review",
    "action": "the specific action to execute",
    "rationale": "why this decision (2-3 sentences max)",
    "success_criteria": ["criteria 1", "criteria 2"],
    "rollback_plan": "what to do if this fails",
    "expected_outcome": {{
        "revenue": 0.00,
        "cost": 0.00,
        "timeline": "24h"
    }}
}}"""

        result = await model_router.call(
            "council_judge",
            prompt,
            system_prompt=RUTHLESS_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
            force_model="glm-5.2",
            context={"estimated_value": 100}
        )

        content = result["content"] if isinstance(result["content"], dict) else {"ruling": "manual_review", "action": str(result["content"])}
        cost = result["usage"]["cost"]

        return {
            "agent": "judge",
            "model": "GLM-5.2",
            "content": content,
            "cost": cost,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_recent_deliberations(self, limit: int = 10) -> List[Dict]:
        """Get recent council deliberations for the observation UI"""
        db = SessionLocal()
        try:
            delibs = db.query(CouncilDeliberation).order_by(
                CouncilDeliberation.created_at.desc()
            ).limit(limit).all()
            return [d.to_dict() for d in delibs]
        finally:
            db.close()


# Global instance
council_agent = CouncilAgent()
