"""
IDEA FACTORY - The 5 Enhancement Agents
========================================
1. Mashup Generator - Combine unrelated niches
2. Etsy Autocomplete - Steal buyer intent
3. Review Miner - Sabotage competitors
4. Bundle Architect - 3x your AOV
5. Pinterest Pilot - Free traffic terrorist
"""

import asyncio
import httpx
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.product import Product, ProductType, Platform, ProductStatus
from models.trend import Trend
from services.model_router import model_router
from services.wiki_service import wiki_service
from prompts.ruthless_system import RUTHLESS_SYSTEM_PROMPT, RUTHLESS_TASKS
from config import SETTINGS


class MashupGenerator:
    """Combine unrelated niches for weird-but-profitable products"""

    def __init__(self):
        self.niches = [
            "anime", "kawaii", "dark aesthetic", "cottagecore", "gaming",
            "fitness", "cooking", "travel", "pets", "music",
            "books", "astrology", "plants", "vintage", "minimalist",
            "y2k", "grunge", "witchy", "coastal", "western"
        ]

    async def generate_mashups(self, count: int = 10) -> List[Dict]:
        """Generate mashup product ideas"""
        pair_gen = await model_router.call(
            "generate_mashup_pairs",
            f"Pick {count} UNIQUE pairs from these niches that would create interesting mashups:\n{self.niches}\n\nRules:\n- No pair should share obvious overlap\n- Prioritize 'weird but intriguing' combinations\n- At least 3 pairs should be 'so weird it might work'\n\nOutput as JSON: {{\"pairs\": [[\"niche_a\", \"niche_b\"], ...]}}",
            system_prompt="You generate creative pairings. Output valid JSON only.",
            response_format={"type": "json_object"},
            force_model="llama-8b",
            temperature=0.9
        )

        pairs = pair_gen["content"].get("pairs", []) if isinstance(pair_gen["content"], dict) else []

        ideas = []
        for pair in pairs[:count]:
            if not isinstance(pair, list) or len(pair) < 2:
                continue
            idea = await model_router.call(
                "generate_mashup_idea",
                f"Create a product idea by mashing up: {pair[0]} + {pair[1]}\n\n{RUTHLESS_TASKS['mashup_ideas']}",
                system_prompt=RUTHLESS_SYSTEM_PROMPT,
                response_format={"type": "json_object"},
                force_model="llama-8b"
            )

            if isinstance(idea["content"], dict):
                idea["content"]["niche_a"] = pair[0]
                idea["content"]["niche_b"] = pair[1]
                ideas.append(idea["content"])
            elif isinstance(idea["content"], list):
                ideas.extend(idea["content"])

        return ideas


class EtsyAutocompleteSpy:
    """Steal buyer intent from Etsy's autocomplete"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def get_suggestions(self, base_keyword: str) -> List[str]:
        """Scrape Etsy autocomplete suggestions"""
        url = f"https://www.etsy.com/api/v3/ajax/member/search-suggestions?q={base_keyword}"

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=10) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    suggestions = [item.get("query", "") for item in data.get("results", [])]
                    return [s for s in suggestions if s and base_keyword.lower() in s.lower()]
        except Exception as e:
            print(f"[EtsyAutocomplete] Error: {e}")

        return []

    async def generate_product_ideas(self, base_keyword: str) -> List[Dict]:
        """Get suggestions and convert to product ideas"""
        suggestions = await self.get_suggestions(base_keyword)

        if not suggestions:
            fallback = await model_router.call(
                "etsy_autocomplete_fallback",
                f"Generate 20 Etsy autocomplete suggestions for: {base_keyword}\n\n{RUTHLESS_TASKS['etsy_autocomplete']}",
                system_prompt=RUTHLESS_SYSTEM_PROMPT,
                response_format={"type": "json_object"},
                force_model="llama-8b"
            )
            return fallback["content"].get("ideas", []) if isinstance(fallback["content"], dict) else []

        analysis = await model_router.call(
            "analyze_etsy_suggestions",
            f"Analyze these Etsy autocomplete suggestions and find the money:\n\nBase keyword: {base_keyword}\nSuggestions: {suggestions}\n\n{RUTHLESS_TASKS['etsy_autocomplete']}",
            system_prompt=RUTHLESS_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
            force_model="llama-70b",
            context={"estimated_value": 50}
        )

        return analysis["content"].get("ideas", []) if isinstance(analysis["content"], dict) else []


class ReviewMiner:
    """Find competitor weaknesses and exploit them"""

    async def mine_reviews(self, product_url: str) -> Dict:
        """Mine reviews from a competitor product"""
        analysis = await model_router.call(
            "mine_competitor_reviews",
            f"""Analyze this competitor product and mine their reviews for weaknesses:

Product URL: {product_url}

{RUTHLESS_TASKS['review_mine']}

Additional context - look for:
1. What do 3-star reviews complain about?
2. What do 1-star reviews rage about?
3. What do 5-star reviews love that could be improved?
4. What's the #1 thing customers wish was different?

Be brutally specific. Quote patterns you'd expect to see.""",
            system_prompt=RUTHLESS_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
            force_model="llama-70b",
            context={"estimated_value": 30}
        )

        return analysis["content"] if isinstance(analysis["content"], dict) else {"complaints": []}

    async def generate_counter_product(self, review_analysis: Dict) -> Dict:
        """Generate a product that specifically fixes competitor weaknesses"""
        counter = await model_router.call(
            "generate_counter_product",
            f"""Based on this competitor weakness analysis, design a BETTER product:

{review_analysis}

Create:
1. Product that solves ALL top 3 complaints
2. Marketing angle that specifically calls out the weakness
3. Design requirements to ensure we don't have same issues
4. Price point that undercuts while maintaining quality

Output JSON:
{{
    "product_type": "sticker",
    "design_requirements": ["req 1", "req 2"],
    "marketing_angle": "the hook that steals their customers",
    "copy_hook": "first line of listing that mentions their pain point",
    "price_strategy": {{
        "our_price": 0.00,
        "competitor_price": 0.00,
        "perceived_value": "why ours is worth more despite lower price"
    }},
    "guarantee": "what we can guarantee that they can't"
}}""",
            system_prompt=RUTHLESS_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
            force_model="llama-8b"
        )

        return counter["content"] if isinstance(counter["content"], dict) else {}


class BundleArchitect:
    """Design bundles that 3x your AOV"""

    async def design_bundles(self, products: List[Dict]) -> List[Dict]:
        """Design bundles from existing products"""
        if len(products) < 3:
            return []

        products_summary = "\n".join([
            f"- {p.get('title', 'Untitled')} (${p.get('price', 0)}) - {p.get('niche', 'unknown')}"
            for p in products
        ])

        bundles = await model_router.call(
            "design_product_bundles",
            f"""Design profit-maximizing bundles from these products:

{products_summary}

{RUTHLESS_TASKS['bundle_architect']}

RULES:
- Each bundle must have 3-7 products
- Bundle price must give "40% off" perception while maintaining 60%+ margin
- Every bundle needs a THEME, not just "pack of X"
- At least one bundle should target gift buyers
- At least one bundle should target "complete set" buyers

Design 3-5 bundles. Output JSON: {{"bundles": [...]}}""",
            system_prompt=RUTHLESS_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
            force_model="llama-8b"
        )

        return bundles["content"].get("bundles", []) if isinstance(bundles["content"], dict) else []

    async def generate_bundle_listing(self, bundle: Dict, products: List[Dict]) -> Dict:
        """Generate complete listing for a bundle"""
        product_ids = bundle.get("product_ids", [])
        included_products = [p for p in products if p.get("id") in product_ids]

        listing = await model_router.call(
            "generate_bundle_listing",
            f"""Create a high-converting bundle listing:

Bundle: {bundle.get('name', 'Untitled')}
Products included:
{chr(10).join([f'- {p.get("title", "")}' for p in included_products])}

Bundle price: ${bundle.get('price', 0)}
Individual total: ${sum(p.get('price', 0) for p in included_products)}
Savings: ${sum(p.get('price', 0) for p in included_products) - bundle.get('price', 0)}

Generate:
1. Title (max 140 chars, includes "Bundle" or "Collection")
2. Description (focus on VALUE and THEME, not just listing products)
3. What makes this bundle special (the theme/story)
4. 5 bullet points of what's included
5. Perfect for... (gift occasions, use cases)
6. Tags (13 max, mix of bundle keywords and individual product keywords)

Output JSON with all fields.""",
            system_prompt=RUTHLESS_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
            force_model="llama-8b"
        )

        return listing["content"] if isinstance(listing["content"], dict) else {}


class PinterestPilot:
    """Automated Pinterest traffic machine"""

    async def create_30_day_plan(self, product: Dict) -> Dict:
        """Create 30-day Pinterest automation plan"""
        plan = await model_router.call(
            "create_pinterest_plan",
            f"""Create a 30-day Pinterest traffic plan for:

Product: {product.get('title', 'Untitled')}
Price: ${product.get('price', 0)}
Niche: {product.get('niche', 'unknown')}
Platform: {product.get('platform', 'etsy')}

{RUTHLESS_TASKS['pinterest_strategy']}

Additional rules:
- First 7 days: 1 pin/day (testing)
- Days 8-30: 2 pins/day (scaling what works)
- Every pin MUST link directly to product
- Focus on keywords, not just aesthetics
- Include seasonal angles if relevant

Output JSON.""",
            system_prompt=RUTHLESS_SYSTEM_PROMPT,
            response_format={"type": "json_object"},
            force_model="llama-8b"
        )

        return plan["content"] if isinstance(plan["content"], dict) else {}

    async def generate_pin_variations(self, base_design_prompt: str, count: int = 5) -> List[Dict]:
        """Generate multiple pin design variations"""
        variations = await model_router.call(
            "generate_pin_variations",
            f"""Generate {count} Pinterest pin design variations for:

Base design: {base_design_prompt}

For EACH variation, provide:
1. Image generation prompt (specific, includes text overlay idea)
2. Title (60 chars max, keyword FIRST)
3. Description (500 chars, keyword-dense)
4. Board name
5. Pin type: "discovery" | "engagement" | "conversion" | "viral"

Variation styles to include:
- Listicle format ("10 X You Need")
- Quote format (inspirational text)
- Comparison format (before/after, this vs that)
- Question format (provocative question)
- Value format (savings, bundle deal)

Output as JSON: {{"pins": [...]}}""",
            system_prompt="You create Pinterest-optimized content.",
            response_format={"type": "json_object"},
            force_model="llama-8b",
            temperature=0.8
        )

        return variations["content"].get("pins", []) if isinstance(variations["content"], dict) else []


class IdeaFactory:
    """Orchestrates all 5 idea generation agents"""

    def __init__(self):
        self.mashup = MashupGenerator()
        self.etsy_spy = EtsyAutocompleteSpy()
        self.review_miner = ReviewMiner()
        self.bundle_arch = BundleArchitect()
        self.pinterest = PinterestPilot()

    async def generate_ideas(self, method: str, **kwargs) -> Dict:
        """Generate ideas using specified method"""
        methods = {
            "mashup": self._mashup_ideas,
            "etsy_autocomplete": self._etsy_autocomplete_ideas,
            "review_mine": self._review_mine_ideas,
            "bundle": self._bundle_ideas,
            "pinterest": self._pinterest_plan,
        }

        handler = methods.get(method)
        if not handler:
            return {"error": f"Unknown method: {method}"}

        return await handler(**kwargs)

    async def _mashup_ideas(self, count: int = 10) -> Dict:
        ideas = await self.mashup.generate_mashups(count)

        for idea in ideas[:3]:
            try:
                await wiki_service.add_entry(
                    title=f"Mashup Idea: {str(idea.get('product_angle', idea.get('angle', 'Unknown')))[:80]}",
                    content=str(idea),
                    category="niche_insight",
                    tags=["mashup", "idea", str(idea.get('niche_a', '')), str(idea.get('niche_b', ''))],
                    confidence=0.6
                )
            except Exception as e:
                print(f"[Wiki] Save error: {e}")

        return {
            "method": "mashup",
            "ideas": ideas,
            "count": len(ideas)
        }

    async def _etsy_autocomplete_ideas(self, keyword: str) -> Dict:
        ideas = await self.etsy_spy.generate_product_ideas(keyword)

        for idea in ideas[:3]:
            try:
                await wiki_service.add_entry(
                    title=f"Etsy Intent: {str(idea.get('suggestion', idea.get('keyword', 'Unknown')))[:80]}",
                    content=str(idea),
                    category="competitor_pattern",
                    tags=["etsy", "autocomplete", "buyer_intent", keyword],
                    niche=keyword,
                    confidence=0.7
                )
            except Exception as e:
                print(f"[Wiki] Save error: {e}")

        return {
            "method": "etsy_autocomplete",
            "keyword": keyword,
            "ideas": ideas,
            "count": len(ideas)
        }

    async def _review_mine_ideas(self, competitor_url: str) -> Dict:
        analysis = await self.review_miner.mine_reviews(competitor_url)
        counter = await self.review_miner.generate_counter_product(analysis)

        try:
            await wiki_service.add_entry(
                title=f"Counter Product: {str(counter.get('marketing_angle', 'Unknown'))[:80]}",
                content=str({"analysis": analysis, "counter": counter}),
                category="competitor_pattern",
                tags=["review_mine", "counter_product", "weakness_exploit"],
                confidence=0.75
            )
        except Exception as e:
            print(f"[Wiki] Save error: {e}")

        return {
            "method": "review_mine",
            "competitor_url": competitor_url,
            "analysis": analysis,
            "counter_product": counter
        }

    async def _bundle_ideas(self, products: List[Dict]) -> Dict:
        bundles = await self.bundle_arch.design_bundles(products)

        return {
            "method": "bundle",
            "bundles": bundles,
            "count": len(bundles)
        }

    async def _pinterest_plan(self, product: Dict) -> Dict:
        plan = await self.pinterest.create_30_day_plan(product)
        variations = await self.pinterest.generate_pin_variations(
            product.get("design_prompt", product.get("title", ""))
        )

        return {
            "method": "pinterest",
            "plan": plan,
            "pin_variations": variations,
            "total_pins": len(variations)
        }

    async def run_full_idea_pipeline(self, niche: str) -> Dict:
        """Run ALL idea generation methods for a niche"""
        results = {
            "niche": niche,
            "timestamp": datetime.utcnow().isoformat(),
            "methods": {}
        }

        print(f"[IdeaFactory] Generating mashups for {niche}...")
        results["methods"]["mashup"] = await self._mashup_ideas(count=5)

        print(f"[IdeaFactory] Mining Etsy autocomplete for {niche}...")
        results["methods"]["etsy_autocomplete"] = await self._etsy_autocomplete_ideas(niche)

        return results


idea_factory = IdeaFactory()
