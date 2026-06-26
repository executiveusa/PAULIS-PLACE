import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from models.product import Product, ProductType, Platform, ProductStatus
from models.trend import Trend
from models.research import NicheInsight, CompetitorProduct
from services.ai_service import ai_service
from config import SETTINGS
from agents.memory_aware_mixin import MemoryAwareAgent, with_memory


class DesignAgent(MemoryAwareAgent):
    """Generates designs based on research and trends"""

    def __init__(self):
        self.output_path = SETTINGS.generated_path
        self.output_path.mkdir(parents=True, exist_ok=True)

    async def create_product_from_trend(
        self,
        trend: Trend,
        niche_insight: NicheInsight,
        product_type: ProductType,
        db: Session
    ) -> Product:
        """Create a new product based on trend data and niche insights"""

        print(f"[DesignAgent] Creating {product_type.value} for trend: {trend.keyword}")

        # 1. Get competitor patterns for this niche
        competitors = db.query(CompetitorProduct).filter(
            CompetitorProduct.niche == trend.niche
        ).order_by(CompetitorProduct.estimated_sales.desc()).limit(10).all()

        competitor_patterns = {
            "design": [c.design_analysis for c in competitors if c.design_analysis],
            "copy": [c.copy_analysis for c in competitors if c.copy_analysis],
        }

        # 2. Generate design prompt
        design_prompt = await ai_service.generate_design_prompt(
            niche=trend.niche,
            trend_data={
                "keyword": trend.keyword,
                "interest_score": trend.interest_score,
                "change_7d": trend.change_7d,
                "related_queries": trend.related_queries[:5],
            },
            competitor_patterns=competitor_patterns,
            product_type=product_type.value
        )

        # 3. Generate the image
        print(f"[DesignAgent] Generating image with prompt: {design_prompt[:100]}...")
        image_b64 = await ai_service.generate_image(design_prompt)

        # 4. Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"{trend.niche}_{product_type.value}_{timestamp}.png"
        image_path = self.output_path / image_filename
        image_path.write_bytes(base64.b64decode(image_b64))

        # 5. Generate variations (for some product types)
        variations = []
        if product_type in [ProductType.STICKER, ProductType.WALL_ART, ProductType.T_SHIRT]:
            print(f"[DesignAgent] Generating variations...")
            var_b64s = await ai_service.generate_image_variations(design_prompt, count=2)
            for i, var_b64 in enumerate(var_b64s):
                var_filename = f"{trend.niche}_{product_type.value}_{timestamp}_var{i+1}.png"
                var_path = self.output_path / var_filename
                var_path.write_bytes(base64.b64decode(var_b64))
                variations.append(str(var_path))

        # 6. Generate listing copy
        competitor_copies = [
            f"Title: {c.title}\nTags: {', '.join(c.tags[:5]) if c.tags else 'N/A'}"
            for c in competitors[:5]
        ]

        listing_copy = await ai_service.generate_listing_copy(
            product_type=product_type.value,
            niche=trend.niche,
            design_description=design_prompt[:500],
            competitor_copies=competitor_copies
        )

        # 7. Determine platform and pricing
        platform = self._determine_platform(product_type)
        price = self._determine_price(product_type, niche_insight)

        # 8. Create product record
        product = Product(
            platform=platform,
            product_type=product_type,
            title=listing_copy['title'],
            description=listing_copy['description'],
            tags=listing_copy['tags'],
            niche=trend.niche,
            design_prompt=design_prompt,
            design_image_path=str(image_path),
            variation_paths=variations,
            price=price,
            status=ProductStatus.PENDING_APPROVAL if not SETTINGS.auto_approve_design else ProductStatus.APPROVED,
            research_data={
                "trend_id": trend.id,
                "trend_keyword": trend.keyword,
                "trend_score": trend.opportunity_score,
            },
            competitor_refs=[c.url for c in competitors[:3] if c.url],
        )

        db.add(product)
        db.commit()
        db.refresh(product)

        # Update trend
        trend.products_created += 1
        trend.last_actioned_at = datetime.utcnow()
        db.commit()

        print(f"[DesignAgent] Created product {product.id}: {product.title[:50]}...")

        return product

    def _determine_platform(self, product_type: ProductType) -> Platform:
        """Determine best platform for product type"""
        mapping = {
            ProductType.STICKER: Platform.ETSY,
            ProductType.WALL_ART: Platform.ETSY,
            ProductType.T_SHIRT: Platform.PRINTIFY,
            ProductType.MUG: Platform.PRINTIFY,
            ProductType.PHONE_CASE: Platform.PRINTIFY,
            ProductType.THUMBNAIL: Platform.FIVERR,
            ProductType.TEMPLATE: Platform.ETSY,
            ProductType.DIGITAL_DOWNLOAD: Platform.ETSY,
            ProductType.GIG: Platform.FIVERR,
        }
        return mapping.get(product_type, Platform.ETSY)

    def _determine_price(self, product_type: ProductType, niche_insight: Optional[NicheInsight]) -> float:
        """Determine pricing based on product type and market data"""
        # Base prices by type
        base_prices = {
            ProductType.STICKER: 3.99,
            ProductType.WALL_ART: 14.99,
            ProductType.T_SHIRT: 24.99,
            ProductType.MUG: 14.99,
            ProductType.PHONE_CASE: 19.99,
            ProductType.THUMBNAIL: 5.00,  # Per thumbnail on Fiverr
            ProductType.TEMPLATE: 6.99,
            ProductType.DIGITAL_DOWNLOAD: 4.99,
            ProductType.GIG: 10.00,  # Fiverr base
        }

        base = base_prices.get(product_type, 9.99)

        # Adjust based on niche data if available
        if niche_insight and niche_insight.avg_price:
            # Aim for middle of market
            base = niche_insight.avg_price * 0.9  # Slightly below average to gain traction

        return round(base, 2)


design_agent = DesignAgent()
