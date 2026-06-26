import httpx
import re
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from models.research import CompetitorProduct, NicheInsight
from models.trend import Trend
from services.ai_service import ai_service
from bs4 import BeautifulSoup


class ResearchAgent:
    """
    The Karpathy approach: Don't guess what works.
    Analyze what's already selling, find patterns, replicate with variation.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def research_niche(self, niche: str, db: Session, max_products: int = 50) -> NicheInsight:
        """Full niche research - scrape top sellers, analyze patterns, find gaps"""
        print(f"[ResearchAgent] Starting full research for: {niche}")

        # 1. Scrape top products from multiple sources
        etsy_products = await self._scrape_etsy(niche, max_products // 2)
        printify_products = await self._scrape_printify_public(niche, max_products // 4)

        all_products = etsy_products + printify_products

        if not all_products:
            print(f"[ResearchAgent] No products found for {niche}")
            return None

        # 2. Analyze each product with AI
        analyzed_products = []
        for product in all_products[:max_products]:
            try:
                analysis = await ai_service.analyze_competitor(product)
                product.update(analysis)
                analyzed_products.append(product)

                # Save to DB
                self._save_competitor(product, niche, db)
            except Exception as e:
                print(f"[ResearchAgent] Error analyzing product: {e}")

        # 3. Aggregate into niche insight
        insight = await self._aggregate_insights(analyzed_products, niche, db)

        return insight

    async def _scrape_etsy(self, niche: str, limit: int) -> list:
        """Scrape Etsy search results for top sellers"""
        products = []

        # Etsy search URL - sort by "best sellers" equivalent
        search_url = f"https://www.etsy.com/search?q={niche}&order=most_relevant"

        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                response = await client.get(search_url, timeout=30)
                soup = BeautifulSoup(response.text, 'html.parser')

                # Parse product cards
                listings = soup.select('[data-listing-id]')

                for listing in listings[:limit]:
                    try:
                        product = {
                            "platform": "etsy",
                            "title": self._clean_text(listing.select_one('h3')),
                            "price": self._extract_price(listing),
                            "url": f"https://www.etsy.com/listing/{listing.get('data-listing-id')}",
                            "external_id": listing.get('data-listing-id'),
                            "rating": self._extract_rating(listing),
                            "review_count": self._extract_review_count(listing),
                            "tags": self._extract_tags(listing),
                            "estimated_sales": self._estimate_etsy_sales(listing),
                        }
                        products.append(product)
                    except Exception as e:
                        continue

        except Exception as e:
            print(f"[ResearchAgent] Etsy scrape error: {e}")

        return products

    async def _scrape_printify_public(self, niche: str, limit: int) -> list:
        """Scrape Printify marketplace/public stores"""
        products = []

        # Printify doesn't have a public marketplace like Etsy
        # We can scrape stores that use Printify (they have /products/ paths with specific structure)
        # For now, return empty - this would need specific store URLs

        return products

    async def _aggregate_insights(self, products: list, niche: str, db: Session) -> NicheInsight:
        """Use AI to aggregate all product analyses into actionable niche insights"""

        # Prepare summary data for AI
        prices = [p.get('price', 0) for p in products if p.get('price')]
        ratings = [p.get('rating', 0) for p in products if p.get('rating')]

        summary = {
            "total_products": len(products),
            "price_stats": {
                "min": min(prices) if prices else 0,
                "max": max(prices) if prices else 0,
                "avg": sum(prices)/len(prices) if prices else 0,
            },
            "rating_avg": sum(ratings)/len(ratings) if ratings else 0,
            "sample_products": products[:20]  # Send top 20 for analysis
        }

        prompt = """You are a digital product market researcher. Analyze these competitor products and extract niche-level insights.

NICHE: {niche}
SUMMARY: {summary}

Analyze ALL products and return JSON:
{{
    "avg_price": recommended price point for new products,
    "price_range": [min, max, p25, p50, p75],
    "avg_rating": average rating observed,
    "total_products_analyzed": count,
    "top_keywords": ["most common keywords across titles", ...],
    "top_tags": ["most common tags", ...],
    "color_palettes": [
        {{"name": "palette name", "colors": ["#hex", ...], "frequency": "how often seen"}},
        ...
    ],
    "style_keywords": ["dominant styles observed", ...],
    "title_patterns": ["common title structures", ...],
    "underserved_subniches": [
        {{"subniche": "name", "evidence": "why it's underserved", "opportunity": "high/medium/low"}},
        ...
    ],
    "pricing_gaps": ["price points with less competition", ...],
    "content_gaps": ["types of content/products missing", ...],
    "product_type_distribution": {{"sticker": count, "wall_art": count, ...}},
    "key_success_factors": ["what makes top sellers successful", ...],
    "common_mistakes_to_avoid": ["what underperformers do wrong", ...]
}}"""

        from openai import OpenAI
        client = OpenAI(api_key=ai_service.client.api_key)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt.format(
                niche=niche,
                summary=json.dumps(summary, indent=2)
            )}],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        insights_data = json.loads(response.choices[0].message.content)

        # Save or update niche insight
        existing = db.query(NicheInsight).filter(NicheInsight.niche == niche).first()

        if existing:
            for key, value in insights_data.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            insight = existing
        else:
            insight = NicheInsight(niche=niche, **insights_data)
            db.add(insight)

        db.commit()
        db.refresh(insight)

        return insight

    def _save_competitor(self, product: dict, niche: str, db: Session):
        """Save competitor product to database"""
        existing = db.query(CompetitorProduct).filter(
            CompetitorProduct.platform == product.get('platform'),
            CompetitorProduct.external_id == product.get('external_id')
        ).first()

        if not existing:
            comp = CompetitorProduct(
                platform=product.get('platform'),
                external_id=product.get('external_id'),
                url=product.get('url'),
                title=product.get('title'),
                price=product.get('price'),
                estimated_sales=product.get('estimated_sales', 0),
                estimated_revenue=product.get('estimated_sales', 0) * product.get('price', 0),
                rating=product.get('rating'),
                review_count=product.get('review_count'),
                tags=product.get('tags', []),
                design_analysis=product.get('design_patterns', {}),
                copy_analysis=product.get('copy_patterns', {}),
                price_analysis=product.get('price_positioning', {}),
                key_patterns=product.get('replication_notes', {}).get('what_to_keep', []),
                replication_notes=product.get('replication_notes', {}),
                niche=niche
            )
            db.add(comp)
            db.commit()

    def _clean_text(self, element) -> str:
        if not element:
            return ""
        return element.get_text(strip=True)

    def _extract_price(self, listing) -> float:
        try:
            price_el = listing.select_one('.currency-value')
            if price_el:
                return float(price_el.get_text(strip=True).replace('$', '').replace(',', ''))
        except:
            pass
        return 0.0

    def _extract_rating(self, listing) -> float:
        try:
            rating_el = listing.select_one('[aria-label*="out of 5 stars"]')
            if rating_el:
                match = re.search(r'([\d.]+)', rating_el.get('aria-label', ''))
                if match:
                    return float(match.group(1))
        except:
            pass
        return 0.0

    def _extract_review_count(self, listing) -> int:
        try:
            review_el = listing.select_one('.wt-text-gray')
            if review_el:
                match = re.search(r'([\d,]+)', review_el.get_text())
                if match:
                    return int(match.group(1).replace(',', ''))
        except:
            pass
        return 0

    def _extract_tags(self, listing) -> list:
        # Etsy tags aren't directly visible on search results
        return []

    def _estimate_etsy_sales(self, listing) -> int:
        """Rough sales estimation based on reviews (Etsy shows ~10-20% of buyers leave reviews)"""
        reviews = self._extract_review_count(listing)
        # Conservative: assume 15% leave reviews
        return int(reviews / 0.15) if reviews > 0 else 0


research_agent = ResearchAgent()
