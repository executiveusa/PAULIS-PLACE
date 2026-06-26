"""
RUTHLESS MODEL ROUTER
=====================
Philosophy: Use the cheapest model that can do the job.
- GLM-5.2: Complex reasoning, strategy, when we MUST be right
- DeepSeek-V2: Bulk generation, drafting, 90% of tasks
- Alpha Owl: Scoring, evaluation, when we need a critic
- Local/GLM-4: Simple classification, tagging, routing
"""

import httpx
import json
import time
from typing import Optional, Literal, Any
from dataclasses import dataclass, field
from enum import Enum
from config import SETTINGS
import asyncio


class ModelTier(str, Enum):
    STRATEGIST = "strategist"      # GLM-5.2 - Expensive, brilliant
    WORKHORSE = "workhorse"        # DeepSeek - Cheap, fast, good enough
    CRITIC = "critic"              # Alpha Owl / Ornith-1 - Good at evaluation
    GRUNT = "grunt"                # GLM-4/Local/Free - Bulk classification


@dataclass
class ModelConfig:
    name: str
    openrouter_id: str
    cost_per_1k_input: float
    cost_per_1k_output: float
    max_tokens: int
    tier: ModelTier
    strengths: list
    weaknesses: list


MODEL_REGISTRY = {
    "glm-5.2": ModelConfig(
        name="GLM-5.2",
        openrouter_id="zhipu-ai/glm-5-2",
        cost_per_1k_input=0.012,
        cost_per_1k_output=0.012,
        max_tokens=8192,
        tier=ModelTier.STRATEGIST,
        strengths=["complex_reasoning", "strategy", "analysis", "code_understanding", "vision"],
        weaknesses=["slow", "expensive"]
    ),
    "deepseek-v2": ModelConfig(
        name="DeepSeek-V2",
        openrouter_id="deepseek/deepseek-chat",
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
        max_tokens=4096,
        tier=ModelTier.WORKHORSE,
        strengths=["generation", "drafting", "summarization", "bulk_tasks"],
        weaknesses=["may_hallucinate_details", "less_strategic"]
    ),
    "deepseek-coder": ModelConfig(
        name="DeepSeek-Coder",
        openrouter_id="deepseek/deepseek-coder",
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
        max_tokens=4096,
        tier=ModelTier.WORKHORSE,
        strengths=["code_generation", "technical_writing"],
        weaknesses=["non_code_tasks"]
    ),
    "alpha-owl": ModelConfig(
        name="Alpha-Owl",
        openrouter_id="alpha-owl/alpha-owl",
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.005,
        max_tokens=4096,
        tier=ModelTier.CRITIC,
        strengths=["evaluation", "scoring", "critique", "quality_assessment"],
        weaknesses=["not_creative", "slow"]
    ),
    "ornith-1": ModelConfig(
        name="Ornith-1",
        openrouter_id="deepreinforce-ai/ornith-1",
        cost_per_1k_input=0.002,
        cost_per_1k_output=0.002,
        max_tokens=4096,
        tier=ModelTier.CRITIC,
        strengths=["agentic_tool_calling", "evaluation", "edge_case_detection", "testing"],
        weaknesses=["not_creative"]
    ),
    "glm-4": ModelConfig(
        name="GLM-4",
        openrouter_id="zhipu-ai/glm-4",
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.001,
        max_tokens=4096,
        tier=ModelTier.GRUNT,
        strengths=["classification", "tagging", "extraction", "routing"],
        weaknesses=["complex_reasoning"]
    ),
    "free-fallback": ModelConfig(
        name="Free-Fallback",
        openrouter_id="openrouter/auto",  # Routes to a free model if available
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        max_tokens=2048,
        tier=ModelTier.GRUNT,
        strengths=["never_breaks", "fallback"],
        weaknesses=["quality_varies", "rate_limited"]
    ),
}

# Task -> Model mapping (the ruthless logic)
TASK_MODEL_MAP = {
    # Strategist tasks - must be right
    "assess_trend_opportunity": "glm-5.2",
    "analyze_competitor": "glm-5.2",
    "generate_strategy": "glm-5.2",
    "evaluate_business_idea": "glm-5.2",
    "complex_research_synthesis": "glm-5.2",
    "extract_money_angles": "glm-5.2",
    "council_judge": "glm-5.2",
    "vision_qa": "glm-5.2",

    # Critic tasks - need evaluation
    "score_product_idea": "alpha-owl",
    "evaluate_design_quality": "alpha-owl",
    "critique_listing_copy": "alpha-owl",
    "assess_competition_level": "alpha-owl",
    "quality_gate_check": "alpha-owl",
    "council_critic": "ornith-1",
    "agentic_tool_test": "ornith-1",

    # Workhorse tasks - bulk generation
    "generate_design_prompt": "deepseek-v2",
    "generate_listing_copy": "deepseek-v2",
    "generate_blog_post": "deepseek-v2",
    "generate_social_post": "deepseek-v2",
    "summarize_content": "deepseek-v2",
    "summarize_for_wiki": "deepseek-v2",
    "extract_patterns": "deepseek-v2",
    "generate_variations": "deepseek-v2",
    "generate_search_queries": "deepseek-v2",
    "synthesize_research": "deepseek-v2",
    "extract_research_actions": "deepseek-v2",
    "execute_search": "deepseek-v2",
    "generate_mashup_pairs": "deepseek-v2",
    "generate_mashup_idea": "deepseek-v2",
    "etsy_autocomplete_fallback": "deepseek-v2",
    "analyze_etsy_suggestions": "glm-5.2",
    "mine_competitor_reviews": "glm-5.2",
    "generate_counter_product": "deepseek-v2",
    "design_product_bundles": "deepseek-v2",
    "generate_bundle_listing": "deepseek-v2",
    "create_pinterest_plan": "deepseek-v2",
    "generate_pin_variations": "deepseek-v2",
    "council_advocate": "deepseek-v2",

    # Grunt tasks - simple classification
    "classify_product_type": "glm-4",
    "extract_tags": "glm-4",
    "route_task": "glm-4",
    "detect_language": "glm-4",
    "simple_qa": "glm-4",
    "identify_research_gaps": "glm-4",
}


class ModelRouter:
    """
    RUTHLESS ROUTING PHILOSOPHY:
    1. Never use a $0.012 model for a $0.00014 task
    2. If DeepSeek can do it 90% as well, use DeepSeek
    3. Only escalate to GLM-5.2 when the cost of being wrong exceeds the model cost
    4. Track actual costs and adjust routing dynamically
    """

    def __init__(self):
        self.api_key = SETTINGS.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.usage_log = []
        self.cost_by_model = {name: 0.0 for name in MODEL_REGISTRY}
        self.cost_by_task = {}

    def get_model_for_task(self, task_type: str) -> ModelConfig:
        """Get the cheapest model that can handle this task"""
        model_name = TASK_MODEL_MAP.get(task_type, "deepseek-v2")  # Default to cheapest
        return MODEL_REGISTRY[model_name]

    def should_escalate(self, task_type: str, context: dict) -> bool:
        """
        Escalation logic: When should we use a more expensive model?
        - High-value decisions (products that could make $100+)
        - Low-confidence situations (conflicting signals)
        - First-time tasks (we don't have patterns yet)
        """
        # High value = escalate
        estimated_value = context.get("estimated_value", 0)
        if estimated_value > 50:  # If this could make $50+, use strategist
            return True

        # Low confidence = escalate
        confidence = context.get("confidence", 0.8)
        if confidence < 0.6:
            return True

        # First time = escalate
        task_count = self.cost_by_task.get(task_type, {}).get("count", 0)
        if task_count < 3:  # First 3 times, use better model
            return True

        return False

    async def call(
        self,
        task_type: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format: Optional[dict] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[dict] = None,
        force_model: Optional[str] = None
    ) -> dict:
        """Main routing call - automatically picks the right model"""
        context = context or {}

        # Determine model
        if force_model:
            model = MODEL_REGISTRY[force_model]
        elif self.should_escalate(task_type, context):
            model = MODEL_REGISTRY["glm-5.2"]
        else:
            model = self.get_model_for_task(task_type)

        # Build request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": SETTINGS.app_url,
            "X-Title": "PAULIS-PLACE"
        }

        payload = {
            "model": model.openrouter_id,
            "messages": [],
            "temperature": temperature,
            "max_tokens": max_tokens or model.max_tokens,
        }

        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})

        if response_format:
            payload["response_format"] = response_format

        # Make call
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    error_detail = response.text
                    # Fallback to workhorse if primary fails
                    if model.tier != ModelTier.WORKHORSE:
                        return await self.call(
                            task_type, prompt, system_prompt, response_format,
                            temperature, max_tokens, context, force_model="deepseek-v2"
                        )
                    # Final fallback to free model
                    return await self.call(
                        task_type, prompt, system_prompt, response_format,
                        temperature, max_tokens, context, force_model="free-fallback"
                    )

                data = response.json()
        except Exception as e:
            # Network failure - try free fallback
            if force_model != "free-fallback":
                return await self.call(
                    task_type, prompt, system_prompt, response_format,
                    temperature, max_tokens, context, force_model="free-fallback"
                )
            raise Exception(f"All model calls failed: {e}")

        # Parse response
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        # Calculate cost
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = (input_tokens / 1000 * model.cost_per_1k_input +
                output_tokens / 1000 * model.cost_per_1k_output)

        # Log usage
        log_entry = {
            "task_type": task_type,
            "model": model.name,
            "tier": model.tier.value,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "timestamp": time.time()
        }
        self.usage_log.append(log_entry)
        self.cost_by_model[model.name] += cost

        if task_type not in self.cost_by_task:
            self.cost_by_task[task_type] = {"cost": 0, "count": 0}
        self.cost_by_task[task_type]["cost"] += cost
        self.cost_by_task[task_type]["count"] += 1

        # Try to parse JSON
        try:
            parsed = json.loads(content)
            return {"content": parsed, "raw": content, "usage": log_entry}
        except Exception:
            return {"content": content, "raw": content, "usage": log_entry}

    async def vision_call(
        self,
        prompt: str,
        image_b64: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        task_type: str = "vision_qa"
    ) -> dict:
        """Vision call for image QA - uses GLM-5.2 vision"""
        model = MODEL_REGISTRY["glm-5.2"]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": SETTINGS.app_url,
            "X-Title": "PAULIS-PLACE"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"}
                }
            ]
        })

        payload = {
            "model": model.openrouter_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = (input_tokens / 1000 * model.cost_per_1k_input +
                output_tokens / 1000 * model.cost_per_1k_output)

        log_entry = {
            "task_type": task_type,
            "model": model.name,
            "tier": model.tier.value,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "timestamp": time.time()
        }
        self.usage_log.append(log_entry)
        self.cost_by_model[model.name] += cost

        try:
            parsed = json.loads(content)
            return {"content": parsed, "raw": content, "usage": log_entry}
        except Exception:
            return {"content": content, "raw": content, "usage": log_entry}

    def get_cost_report(self) -> dict:
        """Get cost breakdown for optimization"""
        return {
            "total_cost": sum(self.cost_by_model.values()),
            "by_model": dict(self.cost_by_model),
            "by_task": dict(self.cost_by_task),
            "call_count": len(self.usage_log),
            "avg_cost_per_call": sum(self.cost_by_model.values()) / max(len(self.usage_log), 1)
        }

    def get_recent_logs(self, limit: int = 50) -> list:
        """Get recent usage logs for the observation console"""
        return self.usage_log[-limit:]


# Global instance
model_router = ModelRouter()
