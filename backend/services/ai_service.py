"""
AI SERVICE - Refactored to use OpenRouter via Model Router
==========================================================
All LLM calls now route through the model_router which:
- Uses OpenRouter (not direct OpenAI)
- Picks the cheapest model per task
- Tracks costs automatically
- Falls back gracefully
"""

import base64
import json
from typing import Optional
from config import SETTINGS
from services.model_router import model_router


class AIService:
    """
    All methods now delegate to model_router.call() which routes
    through OpenRouter to the cheapest capable model.
    """

    def __init__(self):
        self.cost_tracker = {"tokens": 0, "cost": 0.0}

    def _track_from_usage(self, usage: dict):
        """Track cost from model_router usage log"""
        self.cost_tracker["tokens"] += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        self.cost_tracker["cost"] += usage.get("cost", 0.0)

    async def analyze_competitor(self, product_data: dict) -> dict:
        """Analyze a competitor product to extract patterns"""
        prompt = """You are a digital product market analyst. Analyze this competitor product listing and extract actionable patterns for replication.

Product data:
{product_data}

Extract and return JSON with:
{{
    "design_patterns": {{
        "style": "describe visual style",
        "colors": ["list dominant colors"],
        "composition": "layout description",
        "text_elements": ["any text on the product"],
        "mood": "emotional tone"
    }},
    "copy_patterns": {{
        "title_structure": "how title is constructed",
        "key_keywords": ["most important keywords"],
        "value_propositions": ["claims made"],
        "urgency_elements": ["any FOMO/scarcity"]
    }},
    "price_positioning": {{
        "perceived_value": "budget/mid/premium",
        "justification": "why this price works"
    }},
    "replication_notes": {{
        "what_to_keep": ["elements to replicate"],
        "what_to_change": ["elements to differentiate"],
        "improvement_opportunities": ["how to do better"]
    }}
}}"""

        result = await model_router.call(
            "analyze_competitor",
            prompt.format(product_data=json.dumps(product_data, indent=2)),
            response_format={"type": "json_object"},
            temperature=0.3
        )
        self._track_from_usage(result.get("usage", {}))
        content = result["content"]
        return content if isinstance(content, dict) else json.loads(content)

    async def generate_design_prompt(self, niche: str, trend_data: dict, competitor_patterns: dict, product_type: str) -> str:
        """Generate an image generation prompt based on research"""
        prompt = """You are an expert prompt engineer for AI image generation. Create a detailed prompt for generating a {product_type} design.

NICHE: {niche}
TREND DATA: {trend_data}
SUCCESSFUL PATTERNS TO EMULATE: {patterns}

Requirements:
- Be specific about style, colors, composition
- Include anime/kawaii aesthetic cues if relevant to niche
- Make it commercially appealing (clear focal point, readable at thumbnail size)
- Avoid copyrighted characters/brands - create original designs inspired by trends
- Optimize for the product type (stickers need clean edges, wall art can be more complex, etc.)

Return ONLY the image generation prompt, nothing else. Make it detailed (100-200 words)."""

        result = await model_router.call(
            "generate_design_prompt",
            prompt.format(
                product_type=product_type,
                niche=niche,
                trend_data=json.dumps(trend_data),
                patterns=json.dumps(competitor_patterns)
            ),
            temperature=0.7
        )
        self._track_from_usage(result.get("usage", {}))
        return str(result["content"]).strip()

    async def generate_listing_copy(self, product_type: str, niche: str, design_description: str, competitor_copies: list) -> dict:
        """Generate optimized listing title, description, tags"""
        prompt = """You are an Etsy/Printify SEO expert. Write optimized listing copy for a digital product.

PRODUCT TYPE: {product_type}
NICHE: {niche}
DESIGN DESCRIPTION: {design}

EXAMPLES OF SUCCESSFUL COPY IN THIS NICHE:
{examples}

Return JSON:
{{
    "title": "SEO-optimized title, max 140 chars for Etsy, include main keywords early",
    "description": "Full description with keywords naturally woven in, include use cases, mention it makes a great gift, use line breaks for readability. 300-500 words.",
    "tags": ["tag1", "tag2", ...] (13 tags max for Etsy, mix broad and long-tail),
    "alt_text": "Image alt text for accessibility and SEO",
    "category": "suggested Etsy/Printify category path"
}}"""

        result = await model_router.call(
            "generate_listing_copy",
            prompt.format(
                product_type=product_type,
                niche=niche,
                design=design_description,
                examples="\n---\n".join(competitor_copies[:5])
            ),
            response_format={"type": "json_object"},
            temperature=0.6
        )
        self._track_from_usage(result.get("usage", {}))
        content = result["content"]
        return content if isinstance(content, dict) else json.loads(content)

    async def assess_trend_opportunity(self, keyword: str, niche: str, trends_data: dict, market_context: dict) -> dict:
        """Score a trend's opportunity level"""
        prompt = """You are a trend analyst for digital products on Etsy, Printify, and Fiverr. Assess this trend's opportunity.

KEYWORD: {keyword}
NICHE: {niche}
GOOGLE TRENDS DATA: {trends}
MARKET CONTEXT: {market}

Score 0-100 on each dimension and explain reasoning. Return JSON:
{{
    "opportunity_score": 0-100 overall,
    "demand_score": {{"score": 0-100, "reasoning": "..."}},
    "competition_score": {{"score": 0-100, "reasoning": "...", "level": "low/medium/high"}},
    "timing_score": {{"score": 0-100, "reasoning": "...", "is_early": bool}},
    "product_fit_score": {{"score": 0-100, "reasoning": "..."}},
    "product_ideas": [
        {{"type": "sticker/wall_art/t_shirt/etc", "angle": "specific angle to take", "prompt_direction": "what the design should focus on"}}
    ],
    "recommended_action": "create_now/watch/ignore",
    "action_rationale": "why this recommendation"
}}"""

        result = await model_router.call(
            "assess_trend_opportunity",
            prompt.format(
                keyword=keyword,
                niche=niche,
                trends=json.dumps(trends_data),
                market=json.dumps(market_context)
            ),
            response_format={"type": "json_object"},
            temperature=0.4
        )
        self._track_from_usage(result.get("usage", {}))
        content = result["content"]
        return content if isinstance(content, dict) else json.loads(content)

    async def generate_image(self, prompt: str, size: str = "1024x1024", style: str = "vivid") -> str:
        """Generate image using DALL-E 3 via OpenAI (images still need OpenAI directly)"""
        if not SETTINGS.openai_api_key:
            raise Exception("OpenAI API key required for image generation (DALL-E 3 not available via OpenRouter)")

        import openai
        client = openai.OpenAI(api_key=SETTINGS.openai_api_key)

        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            style=style,
            n=1,
            response_format="b64_json"
        )
        self.cost_tracker["cost"] += 0.04 if size == "1024x1024" else 0.08
        return response.data[0].b64_json

    async def generate_image_variations(self, base_prompt: str, count: int = 3) -> list:
        """Generate variations of a design"""
        variations = []
        modifiers = [
            "with a pastel color palette",
            "in a dark/moody aesthetic",
            "with added sparkle/glitter effects",
            "in chibi/super deformed style",
            "with Japanese text elements",
            "in a retro/vintage style"
        ]

        for i in range(min(count, len(modifiers))):
            varied_prompt = f"{base_prompt}. {modifiers[i % len(modifiers)]}"
            b64 = await self.generate_image(varied_prompt)
            variations.append(b64)

        return variations

    def get_cost_today(self) -> float:
        router_cost = model_router.get_cost_report()["total_cost"]
        return self.cost_tracker["cost"] + router_cost


ai_service = AIService()
