"""
RUTHLESS MODEL ROUTER - GROQ POWERED
=====================================
Uses Groq (free, fast) for all LLM calls.
- llama-3.3-70b: Complex reasoning, strategy (strategist tier)
- qwen3-32b: Evaluation, critique (critic tier)
- llama-3.1-8b-instant: Bulk generation, drafting (workhorse tier)
- gpt-oss-20b: Classification, tagging (grunt tier)

Falls back to OpenRouter if Groq fails (when key is valid).
"""

import httpx
import json
import time
from typing import Optional, Any
from dataclasses import dataclass
from enum import Enum
from config import SETTINGS


class ModelTier(str, Enum):
    STRATEGIST = "strategist"
    WORKHORSE = "workhorse"
    CRITIC = "critic"
    GRUNT = "grunt"


@dataclass
class ModelConfig:
    name: str
    provider: str  # "groq" or "openrouter"
    model_id: str
    cost_per_1k_input: float
    cost_per_1k_output: float
    max_tokens: int
    tier: ModelTier
    strengths: list
    weaknesses: list


MODEL_REGISTRY = {
    # Groq models (FREE - primary)
    "llama-70b": ModelConfig(
        name="Llama-3.3-70b",
        provider="groq",
        model_id="llama-3.3-70b-versatile",
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        max_tokens=8192,
        tier=ModelTier.STRATEGIST,
        strengths=["complex_reasoning", "strategy", "analysis", "code_understanding"],
        weaknesses=["not_as_strong_as_gpt4"]
    ),
    "qwen-32b": ModelConfig(
        name="Qwen3-32b",
        provider="groq",
        model_id="qwen/qwen3-32b",
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        max_tokens=4096,
        tier=ModelTier.CRITIC,
        strengths=["evaluation", "scoring", "critique", "quality_assessment"],
        weaknesses=["not_creative"]
    ),
    "llama-8b": ModelConfig(
        name="Llama-3.1-8b",
        provider="groq",
        model_id="llama-3.1-8b-instant",
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        max_tokens=4096,
        tier=ModelTier.WORKHORSE,
        strengths=["generation", "drafting", "summarization", "bulk_tasks", "fast"],
        weaknesses=["less_strategic"]
    ),
    "gpt-oss-20b": ModelConfig(
        name="GPT-OSS-20b",
        provider="groq",
        model_id="openai/gpt-oss-20b",
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        max_tokens=4096,
        tier=ModelTier.GRUNT,
        strengths=["classification", "tagging", "extraction", "routing"],
        weaknesses=["complex_reasoning"]
    ),
    # OpenRouter fallback (if Groq fails)
    "openrouter-fallback": ModelConfig(
        name="OpenRouter-Fallback",
        provider="openrouter",
        model_id="openrouter/auto",
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.001,
        max_tokens=2048,
        tier=ModelTier.GRUNT,
        strengths=["fallback", "never_breaks"],
        weaknesses=["costs_money", "may_fail_if_key_invalid"]
    ),
}

# Task -> Model mapping
TASK_MODEL_MAP = {
    # Strategist tasks
    "assess_trend_opportunity": "llama-70b",
    "analyze_competitor": "llama-70b",
    "generate_strategy": "llama-70b",
    "evaluate_business_idea": "llama-70b",
    "complex_research_synthesis": "llama-70b",
    "extract_money_angles": "llama-70b",
    "council_judge": "llama-70b",
    "vision_qa": "llama-70b",
    "analyze_etsy_suggestions": "llama-70b",
    "mine_competitor_reviews": "llama-70b",
    "analyze_agent_failures": "llama-70b",

    # Critic tasks
    "score_product_idea": "qwen-32b",
    "evaluate_design_quality": "qwen-32b",
    "critique_listing_copy": "qwen-32b",
    "assess_competition_level": "qwen-32b",
    "quality_gate_check": "qwen-32b",
    "council_critic": "qwen-32b",
    "agentic_tool_test": "qwen-32b",

    # Workhorse tasks
    "generate_design_prompt": "llama-8b",
    "generate_listing_copy": "llama-8b",
    "generate_blog_post": "llama-8b",
    "generate_social_post": "llama-8b",
    "summarize_content": "llama-8b",
    "summarize_for_wiki": "llama-8b",
    "extract_patterns": "llama-8b",
    "generate_variations": "llama-8b",
    "generate_search_queries": "llama-8b",
    "synthesize_research": "llama-8b",
    "extract_research_actions": "llama-8b",
    "execute_search": "llama-8b",
    "generate_mashup_pairs": "llama-8b",
    "generate_mashup_idea": "llama-8b",
    "etsy_autocomplete_fallback": "llama-8b",
    "generate_counter_product": "llama-8b",
    "design_product_bundles": "llama-8b",
    "generate_bundle_listing": "llama-8b",
    "create_pinterest_plan": "llama-8b",
    "generate_pin_variations": "llama-8b",
    "council_advocate": "llama-8b",
    "extract_memory_patterns": "llama-8b",
    "analyze_scaffold_steps": "llama-8b",

    # Grunt tasks
    "classify_product_type": "gpt-oss-20b",
    "extract_tags": "gpt-oss-20b",
    "route_task": "gpt-oss-20b",
    "detect_language": "gpt-oss-20b",
    "simple_qa": "gpt-oss-20b",
    "identify_research_gaps": "gpt-oss-20b",
}


class ModelRouter:
    def __init__(self):
        self.groq_api_key = SETTINGS.groq_api_key if hasattr(SETTINGS, 'groq_api_key') else ""
        self.openrouter_api_key = SETTINGS.openrouter_api_key
        self.usage_log = []
        self.cost_by_model = {}
        self.cost_by_task = {}

    def get_model_for_task(self, task_type: str) -> ModelConfig:
        model_name = TASK_MODEL_MAP.get(task_type, "llama-8b")
        return MODEL_REGISTRY[model_name]

    def should_escalate(self, task_type: str, context: dict) -> bool:
        estimated_value = context.get("estimated_value", 0)
        if estimated_value > 50:
            return True
        confidence = context.get("confidence", 0.8)
        if confidence < 0.6:
            return True
        task_count = self.cost_by_task.get(task_type, {}).get("count", 0)
        if task_count < 3:
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
        context = context or {}

        if force_model:
            model = MODEL_REGISTRY[force_model]
        elif self.should_escalate(task_type, context):
            model = MODEL_REGISTRY["llama-70b"]
        else:
            model = self.get_model_for_task(task_type)

        # Try primary provider
        try:
            if model.provider == "groq":
                return await self._call_groq(model, task_type, prompt, system_prompt, response_format, temperature, max_tokens)
            else:
                return await self._call_openrouter(model, task_type, prompt, system_prompt, response_format, temperature, max_tokens)
        except Exception as e:
            print(f"[ModelRouter] {model.name} failed: {e}")
            # Fallback to Groq workhorse
            fallback = MODEL_REGISTRY["llama-8b"]
            try:
                return await self._call_groq(fallback, task_type, prompt, system_prompt, response_format, temperature, max_tokens)
            except Exception as e2:
                print(f"[ModelRouter] Fallback also failed: {e2}")
                raise

    async def _call_groq(
        self, model: ModelConfig, task_type: str, prompt: str,
        system_prompt: Optional[str], response_format: Optional[dict],
        temperature: float, max_tokens: Optional[int]
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or model.max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        # Retry with backoff for rate limits
        max_retries = 3
        for attempt in range(max_retries):
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt
                    print(f"[ModelRouter] Groq rate limited, waiting {wait_time}s (attempt {attempt+1}/{max_retries})")
                    import asyncio
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                data = response.json()
                break
        else:
            raise Exception(f"Groq rate limited after {max_retries} retries")

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
        self.cost_by_model[model.name] = self.cost_by_model.get(model.name, 0.0) + cost

        if task_type not in self.cost_by_task:
            self.cost_by_task[task_type] = {"cost": 0, "count": 0}
        self.cost_by_task[task_type]["cost"] += cost
        self.cost_by_task[task_type]["count"] += 1

        try:
            parsed = json.loads(content)
            return {"content": parsed, "raw": content, "usage": log_entry}
        except Exception:
            return {"content": content, "raw": content, "usage": log_entry}

    async def _call_openrouter(
        self, model: ModelConfig, task_type: str, prompt: str,
        system_prompt: Optional[str], response_format: Optional[dict],
        temperature: float, max_tokens: Optional[int]
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": SETTINGS.app_url,
            "X-Title": "PAULIS-PLACE"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or model.max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
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
        self.cost_by_model[model.name] = self.cost_by_model.get(model.name, 0.0) + cost

        if task_type not in self.cost_by_task:
            self.cost_by_task[task_type] = {"cost": 0, "count": 0}
        self.cost_by_task[task_type]["cost"] += cost
        self.cost_by_task[task_type]["count"] += 1

        try:
            parsed = json.loads(content)
            return {"content": parsed, "raw": content, "usage": log_entry}
        except Exception:
            return {"content": content, "raw": content, "usage": log_entry}

    async def vision_call(
        self, prompt: str, image_b64: str,
        system_prompt: Optional[str] = None, max_tokens: int = 500,
        task_type: str = "vision_qa"
    ) -> dict:
        """Vision call - uses Llama 4 Scout which supports vision on Groq"""
        model = MODEL_REGISTRY["llama-70b"]  # Will use llama-4-scout for vision

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
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
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        log_entry = {
            "task_type": task_type,
            "model": "Llama-4-Scout-Vision",
            "tier": "strategist",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": 0.0,
            "timestamp": time.time()
        }
        self.usage_log.append(log_entry)

        try:
            parsed = json.loads(content)
            return {"content": parsed, "raw": content, "usage": log_entry}
        except Exception:
            return {"content": content, "raw": content, "usage": log_entry}

    def get_cost_report(self) -> dict:
        return {
            "total_cost": sum(self.cost_by_model.values()),
            "by_model": dict(self.cost_by_model),
            "by_task": dict(self.cost_by_task),
            "call_count": len(self.usage_log),
            "avg_cost_per_call": sum(self.cost_by_model.values()) / max(len(self.usage_log), 1)
        }

    def get_recent_logs(self, limit: int = 50) -> list:
        return self.usage_log[-limit:]


model_router = ModelRouter()
