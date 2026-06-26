from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, Text
from datetime import datetime, timezone
from .base import Base


class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(500), index=True)
    niche = Column(String(100), index=True)

    # Google Trends data
    interest_score = Column(Integer)  # 0-100
    interest_history = Column(JSON, default=list)  # Last 90 days
    change_7d = Column(Float, default=0.0)  # % change week over week
    change_30d = Column(Float, default=0.0)

    # Related queries
    related_queries = Column(JSON, default=list)
    related_topics = Column(JSON, default=list)

    # Our assessment
    opportunity_score = Column(Float, default=0.0)  # Our 0-100 score
    competition_level = Column(String(50))  # low, medium, high
    product_ideas = Column(JSON, default=list)

    # Action taken
    products_created = Column(Integer, default=0)
    last_actioned_at = Column(DateTime, nullable=True)

    # Flags
    is_breakout = Column(Boolean, default=False)
    is_seasonal = Column(Boolean, default=False)
    is_evergreen = Column(Boolean, default=False)

    # Timestamps
    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_scanned = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "keyword": self.keyword,
            "niche": self.niche,
            "interest_score": self.interest_score,
            "change_7d": self.change_7d,
            "change_30d": self.change_30d,
            "opportunity_score": self.opportunity_score,
            "competition_level": self.competition_level,
            "product_ideas": self.product_ideas,
            "is_breakout": self.is_breakout,
            "products_created": self.products_created,
            "last_scanned": self.last_scanned.isoformat(),
        }
