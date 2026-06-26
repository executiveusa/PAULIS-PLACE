"""
AUTORESEARCH AGENT - Karpathy-Style Deep Research
==================================================
Philosophy: Don't just search. ITERATE.
1. Search -> 2. Synthesize -> 3. Identify gaps -> 4. Search again -> 5. Repeat
Until we have enough signal to act.
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from services.model_router import model_router, ModelTier
from prompts.ruthless_system import RUTHLESS_SYSTEM_PROMPT, RUTHLESS_TASKS


class ResearchPhase(str, Enum):
    INITIAL_SCAN = "initial_scan"
    DEEP_DIVE = "deep_dive"
    GAP_ANALYSIS = "gap_analysis"
    TARGETED_SEARCH = "targeted_search"
    SYNTHESIS = "synthesis"
    ACTION_EXTRACTION = "action_extraction"
    COMPLETE = "complete"


@dataclass
class ResearchNode:
    """A single piece of knowledge in our graph"""
    id: str
    content: str
    source: str
    confidence: float  # 0-1
    related_nodes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResearchGap:
    """Something we don't know but need to"""
    question: str
    why_important: str
    search_queries: List[str]
    priority: int  # 1-5
    filled: bool = False


@dataclass
class ResearchResult:
    """Final output of research"""
    topic: str
    knowledge_graph: Dict[str, ResearchNode]
    gaps_filled: int
    total_searches: int
    actionable_insights: List[Dict[str, Any]]
    money_angles: List[Dict[str, Any]]
    next_actions: List[str]
    confidence_score: float


class AutoResearchAgent:
    """
    The Research Loop:
    INIT SCAN -> SYNTHESIZE -> GAP ANALYSIS -> TARGET SEARCH -> (loop) -> EXTRACT ACTIONS -> COMPLETE
    """

    def __init__(self):
        self.max_iterations = 3
        self.gap_threshold = 2  # Stop when < 2 high-priority gaps
        self.knowledge_graph: Dict[str, ResearchNode] = {}
        self.gaps: List[ResearchGap] = []
        self.search_count = 0
        self.max_searches = 15  # Cost control

    async def research(
        self,
        topic: str,
        context: Optional[Dict] = None,
        depth: str = "standard"  # "quick", "standard", "deep"
    ) -> ResearchResult:
        """Main research entry point"""
        context = context or {}

        # Configure based on depth
        depth_config = {
            "quick": {"max_iter": 1, "max_searches": 5, "gap_threshold": 5},
            "standard": {"max_iter": 2, "max_searches": 10, "gap_threshold": 3},
            "deep": {"max_iter": 3, "max_searches": 15, "gap_threshold": 1},
        }
        config = depth_config[depth]
        self.max_iterations = config["max_iter"]
        self.max_searches = config["max_searches"]
        self.gap_threshold = config["gap_threshold"]

        # Reset state
        self.knowledge_graph = {}
        self.gaps = []
        self.search_count = 0

        # Phase 1: Initial Scan
        await self._initial_scan(topic, context)

        # Phase 2-4: Iterate
        for i in range(self.max_iterations):
            if self.search_count >= self.max_searches:
                break

            # Synthesize what we know
            synthesis = await self._synthesize()

            # Identify gaps
            self.gaps = await self._identify_gaps(synthesis)

            # Check if we should stop
            high_priority_gaps = [g for g in self.gaps if g.priority >= 4 and not g.filled]
            if len(high_priority_gaps) < self.gap_threshold:
                break

            # Targeted search to fill gaps
            await self._targeted_search()

        # Phase 5: Extract actions
        actions = await self._extract_actions(topic)

        # Phase 6: Extract money angles (RUTHLESS)
        money = await self._extract_money_angles(topic)

        return ResearchResult(
            topic=topic,
            knowledge_graph=self.knowledge_graph,
            gaps_filled=sum(1 for g in self.gaps if g.filled),
            total_searches=self.search_count,
            actionable_insights=actions.get("insights", []),
            money_angles=money.get("angles", []),
            next_actions=money.get("next_actions", []),
            confidence_score=self._calculate_confidence()
        )

    async def _initial_scan(self, topic: str, context: Dict):
        """Phase 1: Get surface-level understanding"""
        query_gen = await model_router.call(
            "generate_search_queries",
            f"Generate 5 search queries to understand: {topic}\n\nContext: {context}\n\nOutput JSON: {{\"queries\": [\"q1\", \"q2\", ...]}}",
            system_prompt="You generate precise search queries. Output as JSON object with 'queries' array.",
            response_format={"type": "json_object"},
            temperature=0.3
        )

        queries = query_gen["content"].get("queries", [topic]) if isinstance(query_gen["content"], dict) else [topic]

        for query in queries[:3]:  # Limit initial scan
            if self.search_count >= self.max_searches:
                break
            await self._execute_search(query, phase=ResearchPhase.INITIAL_SCAN)

    async def _synthesize(self) -> Dict:
        """Phase 2: Make sense of what we know"""
        knowledge_summary = "\n\n".join([
            f"[{node.id}] {node.content} (confidence: {node.confidence})"
            for node in self.knowledge_graph.values()
        ])

        synthesis = await model_router.call(
            "synthesize_research",
            f"SYNTHESIZE this research into a coherent understanding:\n\n{knowledge_summary}",
            system_prompt="""You are a research synthesizer.
Output JSON:
{
    "summary": "2-3 paragraph synthesis",
    "key_findings": ["finding 1", "finding 2"],
    "patterns": ["pattern 1"],
    "contradictions": ["contradiction 1"],
    "confidence_areas": ["what we're confident about"],
    "uncertain_areas": ["what we're not sure about"]
}""",
            response_format={"type": "json_object"},
            force_model="llama-8b"
        )

        return synthesis["content"] if isinstance(synthesis["content"], dict) else {"summary": str(synthesis["content"])}

    async def _identify_gaps(self, synthesis: Dict) -> List[ResearchGap]:
        """Phase 3: What don't we know?"""
        gap_analysis = await model_router.call(
            "identify_research_gaps",
            f"""Based on this synthesis, identify what we NEED to know to take action:

{synthesis}

Generate gaps as JSON:
{{"gaps": [{{
    "question": "specific question to answer",
    "why_important": "why this matters for decision-making",
    "search_queries": ["query 1", "query 2"],
    "priority": 4
}}]}}""",
            system_prompt="You identify knowledge gaps. Be specific about what's missing. Output JSON with 'gaps' array.",
            response_format={"type": "json_object"},
            force_model="gpt-oss-20b"
        )

        gaps = []
        gap_list = gap_analysis["content"].get("gaps", []) if isinstance(gap_analysis["content"], dict) else []
        for gap_data in gap_list:
            try:
                gaps.append(ResearchGap(
                    question=gap_data["question"],
                    why_important=gap_data.get("why_important", ""),
                    search_queries=gap_data.get("search_queries", [gap_data["question"]]),
                    priority=int(gap_data.get("priority", 3))
                ))
            except Exception:
                continue

        return gaps

    async def _targeted_search(self):
        """Phase 4: Search specifically to fill gaps"""
        unfilled_gaps = [g for g in self.gaps if not g.filled]
        unfilled_gaps.sort(key=lambda g: g.priority, reverse=True)

        for gap in unfilled_gaps[:3]:  # Top 3 gaps
            if self.search_count >= self.max_searches:
                break

            for query in gap.search_queries[:2]:  # 2 queries per gap
                if self.search_count >= self.max_searches:
                    break
                await self._execute_search(
                    query,
                    phase=ResearchPhase.TARGETED_SEARCH,
                    gap_id=gap.question
                )

            gap.filled = True

    async def _extract_actions(self, topic: str) -> Dict:
        """Phase 5: What should we DO with this knowledge?"""
        knowledge_summary = "\n".join([
            f"- {node.content}"
            for node in self.knowledge_graph.values()
        ])

        actions = await model_router.call(
            "extract_research_actions",
            f"""Extract ACTIONABLE insights from this research about {topic}:

{knowledge_summary}

Output JSON:
{{
    "insights": [
        {{
            "insight": "the insight",
            "action": "what to do about it",
            "effort": "low",
            "impact": "high",
            "timeline": "immediate"
        }}
    ]
}}""",
            system_prompt="You extract actionable insights. Every insight must have a concrete action.",
            response_format={"type": "json_object"},
            force_model="llama-8b"
        )

        return actions["content"] if isinstance(actions["content"], dict) else {"insights": []}

    async def _extract_money_angles(self, topic: str) -> Dict:
        """Phase 6: RUTHLESS money extraction"""
        knowledge_summary = "\n".join([
            f"- {node.content}"
            for node in self.knowledge_graph.values()
        ])

        money = await model_router.call(
            "extract_money_angles",
            f"""RUTHLESS MONEY ANGLE ANALYSIS for: {topic}

Research findings:
{knowledge_summary}

Apply the RUTHLESS framework:
1. What's already making money in this space?
2. How can we copy it faster/cheaper?
3. What's the fastest path to first dollar?

Output JSON:
{{
    "angles": [
        {{
            "angle": "money-making angle description",
            "proof": ["url or example of this working"],
            "pattern": "what makes it work",
            "replication": "how to copy in <24 hours",
            "cost_to_make": 0.00,
            "price_to_sell": 0.00,
            "units_to_break_even": 0,
            "expected_monthly_revenue": 0.00,
            "confidence": 0.0
        }}
    ],
    "next_actions": ["immediate action 1", "immediate action 2"]
}}""",
            system_prompt=RUTHLESS_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
            force_model="llama-70b",
            context={"estimated_value": 100}
        )

        return money["content"] if isinstance(money["content"], dict) else {"angles": [], "next_actions": []}

    async def _execute_search(self, query: str, phase: ResearchPhase, gap_id: Optional[str] = None):
        """Execute a single search and add to knowledge graph"""
        self.search_count += 1

        search_result = await model_router.call(
            "execute_search",
            f"Search result for: {query}\n\nProvide factual, specific information. Include sources/URLs if possible.",
            system_prompt="You are a search engine. Provide factual results. Be specific, not vague.",
            force_model="llama-8b",
            temperature=0.3
        )

        node_id = f"search_{self.search_count}"
        content = search_result["content"] if isinstance(search_result["content"], str) else str(search_result["content"])

        node = ResearchNode(
            id=node_id,
            content=content,
            source=f"search:{query}",
            confidence=0.7 if phase == ResearchPhase.INITIAL_SCAN else 0.8,
            tags=[phase.value, query[:50]]
        )

        self.knowledge_graph[node_id] = node

        if gap_id and gap_id in [g.question for g in self.gaps]:
            node.related_nodes.append(gap_id)

    def _calculate_confidence(self) -> float:
        """Calculate overall confidence in research"""
        if not self.knowledge_graph:
            return 0.0

        nodes = list(self.knowledge_graph.values())
        avg_confidence = sum(n.confidence for n in nodes) / len(nodes)

        filled_ratio = sum(1 for g in self.gaps if g.filled) / max(len(self.gaps), 1)

        return min(1.0, (avg_confidence * 0.7) + (filled_ratio * 0.3))


# Global instance
autoresearch_agent = AutoResearchAgent()
