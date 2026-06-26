from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base
import enum


class Platform(str, enum.Enum):
    ETSY = "etsy"
    PRINTIFY = "printify"
    FIVERR = "fiverr"


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PUBLISHED = "published"
    DELISTED = "delisted"
    FAILED = "failed"


class ProductType(str, enum.Enum):
    STICKER = "sticker"
    WALL_ART = "wall_art"
    T_SHIRT = "t_shirt"
    MUG = "mug"
    PHONE_CASE = "phone_case"
    THUMBNAIL = "thumbnail"
    TEMPLATE = "template"
    DIGITAL_DOWNLOAD = "digital_download"
    GIG = "fiverr_gig"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, nullable=True)  # Platform's ID
    platform = Column(Enum(Platform))
    product_type = Column(Enum(ProductType))

    # Content
    title = Column(String(500))
    description = Column(Text)
    tags = Column(JSON, default=list)
    niche = Column(String(100))

    # Assets
    design_prompt = Column(Text)
    design_image_path = Column(String(500))
    variation_paths = Column(JSON, default=list)
    thumbnail_path = Column(String(500))

    # Pricing
    price = Column(Float)
    currency = Column(String(10), default="USD")

    # Status
    status = Column(Enum(ProductStatus), default=ProductStatus.DRAFT)
    requires_approval = Column(Boolean, default=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(100), nullable=True)

    # Research backing
    research_data = Column(JSON, nullable=True)  # What trend/research led to this
    competitor_refs = Column(JSON, default=list)  # URLs of similar top sellers

    # Metrics
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    sales = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime, nullable=True)

    # Printify specific
    printify_blueprint_id = Column(String(100), nullable=True)
    printify_variant_ids = Column(JSON, default=list)

    def to_dict(self):
        return {
            "id": self.id,
            "external_id": self.external_id,
            "platform": self.platform.value,
            "product_type": self.product_type.value,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "niche": self.niche,
            "price": self.price,
            "currency": self.currency,
            "status": self.status.value,
            "views": self.views,
            "clicks": self.clicks,
            "sales": self.sales,
            "revenue": self.revenue,
            "created_at": self.created_at.isoformat(),
            "research_data": self.research_data,
        }
