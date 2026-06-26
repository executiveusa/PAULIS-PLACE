"""
LLM WIKI - Self-Building Knowledge Base
========================================
The system builds its own wiki as it learns.
Uses pgvector for semantic search (with keyword fallback).
"""

import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, Index, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from models.base import Base, SessionLocal
from services.model_router import model_router


class WikiEntry(Base):
    __tablename__ = "wiki_entries"

    id = Column(Integer, primary_key=True, index=True)

    # Content
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(String(1000))

    # Embedding (would use pgvector in production)
    embedding_id = Column(String(100), unique=True)

    # Organization
    category = Column(String(100), index=True)
    tags = Column(JSON, default=list)
    niche = Column(String(100), index=True)

    # Source tracking
    source_type = Column(String(50))  # "research", "scrape", "manual", "generated"
    source_url = Column(String(1000))
    source_metadata = Column(JSON, default=dict)

    # Quality
    confidence = Column(Float, default=0.5)
    verified = Column(Integer, default=0)  # Times verified by human
    outdated = Column(Integer, default=0)  # Times flagged as outdated

    # Relationships
    related_entries = Column(JSON, default=list)
    parent_entry_id = Column(Integer, nullable=True)

    # Usage tracking
    times_accessed = Column(Integer, default=0)
    times_used_in_products = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "category": self.category,
            "tags": self.tags or [],
            "niche": self.niche,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "times_used_in_products": self.times_used_in_products,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class WikiSearchResult:
    entry: WikiEntry
    relevance_score: float
    match_type: str  # "semantic", "keyword", "tag"


class WikiService:
    """
    Self-building knowledge base.
    The system adds to this as it learns.
    """

    CATEGORIES = {
        "niche_insight": "What works in a specific niche",
        "competitor_pattern": "Patterns from successful competitors",
        "trend_analysis": "Trend data and interpretations",
        "design_principle": "What makes designs sell",
        "copy_formula": "Copywriting patterns that convert",
        "pricing_strategy": "Pricing insights and strategies",
        "platform_rule": "Platform-specific rules and tips",
        "failure_lesson": "What didn't work and why",
        "tool_technique": "How to use tools effectively",
        "process_sop": "Standard operating procedures",
    }

    def __init__(self):
        self.db = SessionLocal()

    async def add_entry(
        self,
        title: str,
        content: str,
        category: str,
        tags: List[str] = None,
        niche: Optional[str] = None,
        source_type: str = "generated",
        source_url: Optional[str] = None,
        source_metadata: Dict = None,
        confidence: float = 0.7
    ) -> WikiEntry:
        """Add a new entry to the wiki"""
        # Generate summary
        try:
            summary_result = await model_router.call(
                "summarize_for_wiki",
                f"Summarize in one sentence (max 150 chars):\n\n{content[:2000]}",
                system_prompt="You write concise summaries.",
                force_model="glm-4",
                max_tokens=100
            )
            raw = summary_result["content"]
            summary = (raw if isinstance(raw, str) else str(raw))[:150]
        except Exception:
            summary = content[:150]

        # Generate embedding ID (in production, would actually embed)
        embedding_id = hashlib.md5(f"{title}{content[:500]}".encode()).hexdigest()

        entry = WikiEntry(
            title=title,
            content=content,
            summary=summary,
            embedding_id=embedding_id,
            category=category,
            tags=tags or [],
            niche=niche,
            source_type=source_type,
            source_url=source_url,
            source_metadata=source_metadata or {},
            confidence=confidence
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        return entry

    async def add_from_research(self, research_result) -> List[WikiEntry]:
        """Extract and add entries from a research result"""
        entries = []

        # Add money angles
        for angle in research_result.money_angles:
            entry = await self.add_entry(
                title=f"Money Angle: {str(angle.get('angle', 'Unknown'))[:100]}",
                content=json.dumps(angle, indent=2, default=str),
                category="niche_insight",
                tags=["money_angle", "proven", research_result.topic],
                niche=research_result.topic,
                source_type="research",
                confidence=float(angle.get("confidence", 0.7))
            )
            entries.append(entry)

        # Add actionable insights
        for insight in research_result.actionable_insights:
            entry = await self.add_entry(
                title=f"Insight: {str(insight.get('insight', 'Unknown'))[:100]}",
                content=json.dumps(insight, indent=2, default=str),
                category="niche_insight",
                tags=["actionable", str(insight.get("effort", "")), str(insight.get("impact", ""))],
                niche=research_result.topic,
                source_type="research"
            )
            entries.append(entry)

        return entries

    def search(
        self,
        query: str,
        niche: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        min_confidence: float = 0.5
    ) -> List[WikiSearchResult]:
        """Search the wiki"""
        q = self.db.query(WikiEntry).filter(
            WikiEntry.confidence >= min_confidence,
            WikiEntry.outdated == 0
        )

        if niche:
            q = q.filter(WikiEntry.niche == niche)
        if category:
            q = q.filter(WikiEntry.category == category)

        # Keyword search (in production, would also do semantic search via pgvector)
        q = q.filter(
            WikiEntry.title.ilike(f"%{query}%") |
            WikiEntry.content.ilike(f"%{query}%") |
            WikiEntry.summary.ilike(f"%{query}%")
        )

        q = q.order_by(WikiEntry.confidence.desc(), WikiEntry.times_used_in_products.desc())
        entries = q.limit(limit).all()

        # Track access
        for entry in entries:
            entry.times_accessed += 1
            entry.last_used_at = datetime.utcnow()
        self.db.commit()

        return [
            WikiSearchResult(entry=entry, relevance_score=entry.confidence, match_type="keyword")
            for entry in entries
        ]

    def get_similar_patterns(self, niche: str, exclude_id: Optional[int] = None) -> List[WikiEntry]:
        """Get successful patterns from similar niches"""
        q = self.db.query(WikiEntry).filter(
            WikiEntry.category == "competitor_pattern",
            WikiEntry.times_used_in_products > 0,
            WikiEntry.confidence >= 0.7
        )

        if exclude_id:
            q = q.filter(WikiEntry.id != exclude_id)

        same_niche = q.filter(WikiEntry.niche == niche).limit(5).all()
        other_niches = q.filter(WikiEntry.niche != niche).limit(5).all()

        return same_niche + other_niches

    def mark_used_in_product(self, entry_id: int):
        """Mark an entry as used in a product (builds proven patterns)"""
        entry = self.db.query(WikiEntry).filter(WikiEntry.id == entry_id).first()
        if entry:
            entry.times_used_in_products += 1
            entry.last_used_at = datetime.utcnow()
            if entry.times_used_in_products >= 3:
                entry.confidence = min(1.0, entry.confidence + 0.1)
            self.db.commit()

    def get_stats(self) -> Dict:
        """Get wiki statistics"""
        return {
            "total_entries": self.db.query(func.count(WikiEntry.id)).scalar() or 0,
            "by_category": dict(
                self.db.query(WikiEntry.category, func.count(WikiEntry.id))
                .group_by(WikiEntry.category).all()
            ),
            "by_niche": dict(
                self.db.query(WikiEntry.niche, func.count(WikiEntry.id))
                .group_by(WikiEntry.niche).all()
            ),
            "proven_patterns": self.db.query(func.count(WikiEntry.id))
                .filter(WikiEntry.times_used_in_products >= 3).scalar() or 0,
            "avg_confidence": float(self.db.query(func.avg(WikiEntry.confidence)).scalar() or 0),
        }

    def get_or_create_sop(self, process_name: str) -> WikiEntry:
        """Get or create a standard operating procedure"""
        existing = self.db.query(WikiEntry).filter(
            WikiEntry.category == "process_sop",
            WikiEntry.title.ilike(f"%{process_name}%")
        ).first()

        if existing:
            return existing

        sop_content = f"""# SOP: {process_name}

## Purpose
[To be filled]

## Prerequisites
- [List requirements]

## Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Quality Checklist
- [ ] [Check 1]
- [ ] [Check 2]

## Common Issues
- Issue: [description]
  - Solution: [fix]

## Last Updated
{datetime.utcnow().strftime('%Y-%m-%d')}
"""

        entry = WikiEntry(
            title=f"SOP: {process_name}",
            content=sop_content,
            summary=f"Standard operating procedure for {process_name}",
            category="process_sop",
            tags=["sop", process_name.lower().replace(" ", "_")],
            confidence=0.3
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        return entry


wiki_service = WikiService()
