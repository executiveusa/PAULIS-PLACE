"""
PROFILE ROUTER — Spec §8 task-profile -> model mapping
=====================================================
Hermes never picks a model. It declares a task profile.
This module maps spec profiles to concrete model IDs across providers
already wired in services/model_router.py + services/ai_service.py.

Profiles: plan, judge, implement, write_short, write_long, score, test, docs

Strategy:
 1. Try the preferred model (via OpenRouter for paid models, Groq for free ones).
 2. Fall back to the fallback model.
 3. The judge profile MUST differ from the worker profile when used in the
    same envelope (enforced in services/judge.py).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

try:
    from config import SETTINGS
except Exception:  # pragma: no cover
    SETTINGS = None


@dataclass
class ProfileSpec:
    profile: str
    preferred_model: str
    preferred_provider: str  # "openrouter" | "groq" | "openai" | "anthropic"
    fallback_model: str
    fallback_provider: str
    temperature: float = 0.4
    max_tokens: int = 2048
    supports_json: bool = True


PROFILE_REGISTRY: dict[str, ProfileSpec] = {
    "plan": ProfileSpec(
        "plan",
        preferred_model="anthropic/claude-opus-4.5",
        preferred_provider="openrouter",
        fallback_model="z-ai/glm-4.6",
        fallback_provider="openrouter",
        temperature=0.3, max_tokens=4096,
    ),
    "judge": ProfileSpec(
        "judge",
        preferred_model="anthropic/claude-opus-4.5",
        preferred_provider="openrouter",
        fallback_model="z-ai/glm-4.6",
        fallback_provider="openrouter",
        temperature=0.2, max_tokens=2048,
    ),
    "implement": ProfileSpec(
        "implement",
        preferred_model="openai/gpt-5",
        preferred_provider="openrouter",
        fallback_model="z-ai/glm-5.2",
        fallback_provider="openrouter",
        temperature=0.2, max_tokens=6144,
    ),
    "write_short": ProfileSpec(
        "write_short",
        preferred_model="x-ai/grok-4.5-fast",
        preferred_provider="openrouter",
        fallback_model="z-ai/glm-5.2",
        fallback_provider="openrouter",
        temperature=0.6, max_tokens=1024,
    ),
    "write_long": ProfileSpec(
        "write_long",
        preferred_model="moonshotai/kimi-k3",
        preferred_provider="openrouter",
        fallback_model="z-ai/glm-4.6",
        fallback_provider="openrouter",
        temperature=0.5, max_tokens=8192,
    ),
    "score": ProfileSpec(
        "score",
        preferred_model="qwen/qwen-3.5",
        preferred_provider="openrouter",
        fallback_model="meta-llama/llama-3.1-70b-instruct",
        fallback_provider="openrouter",
        temperature=0.2, max_tokens=1024,
    ),
    "test": ProfileSpec(
        "test",
        preferred_model="moonshotai/kimi-k3",
        preferred_provider="openrouter",
        fallback_model="z-ai/glm-5.2",
        fallback_provider="openrouter",
        temperature=0.1, max_tokens=6144,
    ),
    "docs": ProfileSpec(
        "docs",
        preferred_model="qwen/qwen-2.5-7b-instruct",
        preferred_provider="openrouter",
        fallback_model="meta-llama/llama-3.1-8b-instruct",
        fallback_provider="groq",
        temperature=0.3, max_tokens=1024,
    ),
}


def resolve_profile(profile_name: str) -> ProfileSpec:
    if profile_name not in PROFILE_REGISTRY:
        raise ValueError(f"unknown profile: {profile_name}")
    return PROFILE_REGISTRY[profile_name]


def ensure_distinct_profiles(worker_profile: str, judge_profile: str) -> None:
    """Spec §8 — judge cannot be same model that produced the work."""
    if worker_profile == judge_profile:
        raise ValueError(
            f"judge profile '{judge_profile}' must differ from worker profile '{worker_profile}'"
        )
    w = resolve_profile(worker_profile)
    j = resolve_profile(judge_profile)
    if w.preferred_model == j.preferred_model:
        raise ValueError(
            f"judge model '{j.preferred_model}' equals worker model — pick different profile"
        )


async def call_profile(
    profile_name: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    response_format_json: bool = False,
) -> dict:
    """Call the model behind a task profile. Returns {content, raw, usage, model, profile}."""
    spec = resolve_profile(profile_name)

    # Route through model_router's OpenRouter client (already implemented)
    # by using force_model with a synthetic model name we register on the fly.
    from services.model_router import MODEL_REGISTRY, model_router, ModelConfig, ModelTier  # type: ignore

    key = f"profile::{profile_name}"
    if key not in MODEL_REGISTRY:
        MODEL_REGISTRY[key] = ModelConfig(
            name=f"profile-{profile_name}",
            provider="openrouter",
            model_id=spec.preferred_model,
            cost_per_1k_input=0.0,  # metered by OpenRouter; tracked upstream
            cost_per_1k_output=0.0,
            max_tokens=spec.max_tokens,
            tier=ModelTier.WORKHORSE,
            strengths=[],
            weaknesses=[],
        )

    payload_kwargs = dict(
        task_type=f"profile::{profile_name}",
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature if temperature is not None else spec.temperature,
        max_tokens=max_tokens or spec.max_tokens,
        force_model=key,
    )
    if response_format_json:
        payload_kwargs["response_format"] = {"type": "json_object"}

    try:
        result = await model_router.call(**payload_kwargs)
    except Exception:
        # Fallback path
        fallback_key = f"profile::{profile_name}::fallback"
        if fallback_key not in MODEL_REGISTRY:
            MODEL_REGISTRY[fallback_key] = ModelConfig(
                name=f"profile-{profile_name}-fallback",
                provider="openrouter",
                model_id=spec.fallback_model,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                max_tokens=spec.max_tokens,
                tier=ModelTier.WORKHORSE,
                strengths=[],
                weaknesses=[],
            )
        payload_kwargs["force_model"] = fallback_key
        result = await model_router.call(**payload_kwargs)

    result["profile"] = profile_name
    result["model"] = result.get("usage", {}).get("model", spec.preferred_model)
    return result


def cost_today() -> float:
    """Total AI spend today across all profiles + tasks."""
    from services.model_router import model_router  # type: ignore
    return float(model_router.get_cost_report()["total_cost"])


def cap_remaining(cap_usd: float = 25.0) -> float:
    return max(0.0, cap_usd - cost_today())