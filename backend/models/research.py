from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from datetime import datetime, timezone
from .base import Base


class CompetitorProduct(Base):
    """Snapshot of a top-selling product we're analyzing"""
    __tablename__ = "competitor_products"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50))
    external_id = Column(String(200))
    url = Column(String(1000))

    # Product data
    title = Column(String(500))
    price = Column(Float)
    currency = Column(String(10))
    estimated_sales = Column(Integer)
    estimated_revenue = Column(Float)
    rating = Column(Float)
    review_count = Column(Integer)
    tags = Column(JSON, default=list)

    # Analysis
    design_analysis = Column(JSON, default=dict)  # Colors, style, composition
    copy_analysis = Column(JSON, default=dict)  # Title patterns, keywords
    price_analysis = Column(JSON, default=dict)

    # What we learned
    key_patterns = Column(JSON, default=list)
    replication_notes = Column(JSON, default=dict)

    niche = Column(String(100))
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "platform": self.platform,
            "title": self.title,
            "price": self.price,
            "estimated_sales": self.estimated_sales,
            "estimated_revenue": self.estimated_revenue,
            "rating": self.rating,
            "review_count": self.review_count,
            "key_patterns": self.key_patterns,
            "niche": self.niche,
        }


class NicheInsight(Base):
    """Aggregated insights about a niche"""
    __tablename__ = "niche_insights"

    id = Column(Integer, primary_key=True, index=True)
    niche = Column(String(100), unique=True, index=True)

    # Market data
    avg_price = Column(Float)
    price_range = Column(JSON, default=list)  # [min, max, p25, p50, p75]
    avg_rating = Column(Float)
    total_products_analyzed = Column(Integer)

    # Patterns
    top_keywords = Column(JSON, default=list)
    top_tags = Column(JSON, default=list)
    color_palettes = Column(JSON, default=list)
    style_keywords = Column(JSON, default=list)
    title_patterns = Column(JSON, default=list)

    # Gaps
    underserved_subniches = Column(JSON, default=list)
    pricing_gaps = Column(JSON, default=list)
    content_gaps = Column(JSON, default=list)

    # Product type distribution
    product_type_distribution = Column(JSON, default=dict)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "niche": self.niche,
            "avg_price": self.avg_price,
            "total_products_analyzed": self.total_products_analyzed,
            "top_keywords": self.top_keywords[:20],
            "underserved_subniches": self.underserved_subniches[:10],
            "product_type_distribution": self.product_type_distribution,
            "updated_at": self.updated_at.isoformat(),
        }
