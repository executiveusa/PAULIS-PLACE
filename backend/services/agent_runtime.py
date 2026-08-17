"""Production model runtime for Pauli agents.

AgentForge patterns intentionally adopted here:
- persistent agent/persona is separate from model/provider selection
- explicit modality/capability contracts
- bounded retries with exponential backoff
- non-retriable setup/auth failures fail immediately
- empty responses are failures
- async provider I/O

Pauli-specific hardening:
- no silent provider fallback for auth/setup errors
- every selected route is returned as structured metadata so callers can persist it
- no provider is treated as canonical agent identity
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from config import SETTINGS


class RuntimeErrorBase(Exception):
    """Base class for governed runtime errors."""


class NonRetriableRuntimeError(RuntimeErrorBase):
    """Configuration, authentication, policy, or unsupported-capability failure."""


class TransientRuntimeError(RuntimeErrorBase):
    """Network/rate-limit/provider failure that may succeed on retry."""


class EmptyRuntimeResponse(RuntimeErrorBase):
    """Provider returned an unusable response."""


@dataclass(frozen=True)
class AgentPersona:
    agent_key: str
    name: str
    role: str
    specialty: str = ""
    identity: dict[str, Any] = field(default_factory=dict)
    heart: dict[str, Any] = field(default_factory=dict)
    soul: dict[str, Any] = field(default_factory=dict)
    skill_manifest: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelRoute:
    route_key: str
    provider: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 4096


@dataclass(frozen=True)
class RuntimeRequest:
    persona: AgentPersona
    route: ModelRoute
    task_key: str
    mission_title: str
    mission_intent: str
    requested_outcome: str
    task_description: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeResult:
    content: Any
    raw: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    attempts: int = 1


class OpenAICompatibleProvider:
    def __init__(self, *, name: str, base_url: str, api_key: str, timeout_seconds: float = 120.0):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def generate(self, request: RuntimeRequest, max_attempts: int = 3) -> RuntimeResult:
        if not self.configured:
            raise NonRetriableRuntimeError(f"provider '{self.name}' is not configured")

        system_prompt = build_system_prompt(request.persona)
        user_prompt = build_task_prompt(request)
        payload = {
            "model": request.route.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": request.route.temperature,
            "max_tokens": request.route.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.name == "openrouter":
            headers["HTTP-Referer"] = SETTINGS.app_url
            headers["X-Title"] = "PAULIS-PLACE"

        last_error: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                started = asyncio.get_running_loop().time()
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                latency_ms = int((asyncio.get_running_loop().time() - started) * 1000)

                if response.status_code in {400, 401, 403, 404, 405, 422}:
                    raise NonRetriableRuntimeError(
                        f"{self.name} rejected request ({response.status_code}): {response.text[:240]}"
                    )
                if response.status_code == 429 or response.status_code == 408 or response.status_code >= 500:
                    raise TransientRuntimeError(
                        f"{self.name} transient error ({response.status_code}): {response.text[:240]}"
                    )
                response.raise_for_status()
                body = response.json()
                raw = str(body.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
                if not raw:
                    raise EmptyRuntimeResponse(f"{self.name} returned an empty response")
                usage = body.get("usage", {}) or {}
                return RuntimeResult(
                    content=raw,
                    raw=raw,
                    provider=self.name,
                    model=request.route.model,
                    input_tokens=int(usage.get("prompt_tokens", 0) or 0),
                    output_tokens=int(usage.get("completion_tokens", 0) or 0),
                    latency_ms=latency_ms,
                    attempts=attempt,
                )
            except NonRetriableRuntimeError:
                raise
            except EmptyRuntimeResponse:
                raise
            except (httpx.TimeoutException, httpx.NetworkError, TransientRuntimeError) as exc:
                last_error = exc
                if attempt >= max_attempts:
                    break
                await asyncio.sleep(2 ** (attempt - 1))
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= max_attempts:
                    break
                await asyncio.sleep(2 ** (attempt - 1))

        raise TransientRuntimeError(f"{self.name} exhausted {max_attempts} attempts: {last_error}")


PROVIDERS = {
    "groq": OpenAICompatibleProvider(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        api_key=getattr(SETTINGS, "groq_api_key", ""),
        timeout_seconds=60.0,
    ),
    "openrouter": OpenAICompatibleProvider(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key=getattr(SETTINGS, "openrouter_api_key", ""),
        timeout_seconds=120.0,
    ),
}


DEFAULT_ROUTES: dict[str, list[ModelRoute]] = {
    "plan": [
        ModelRoute("plan:primary", "openrouter", "anthropic/claude-opus-4.5", 0.25, 4096),
        ModelRoute("plan:fallback", "groq", "llama-3.3-70b-versatile", 0.25, 4096),
    ],
    "critique": [
        ModelRoute("critique:primary", "groq", "qwen/qwen3-32b", 0.15, 3072),
        ModelRoute("critique:fallback", "openrouter", "anthropic/claude-opus-4.5", 0.15, 3072),
    ],
    "guardian": [
        ModelRoute("guardian:primary", "openrouter", "anthropic/claude-opus-4.5", 0.1, 2048),
        ModelRoute("guardian:fallback", "groq", "llama-3.3-70b-versatile", 0.1, 2048),
    ],
    "default": [
        ModelRoute("default:primary", "groq", "llama-3.3-70b-versatile", 0.3, 4096),
        ModelRoute("default:fallback", "openrouter", "openrouter/auto", 0.3, 4096),
    ],
}


class AgentRuntime:
    """Route a bounded cognitive task to configured model providers."""

    def candidate_routes(self, task_key: str) -> list[ModelRoute]:
        return list(DEFAULT_ROUTES.get(task_key, DEFAULT_ROUTES["default"]))

    async def execute(self, request_factory, task_key: str) -> RuntimeResult:
        routes = self.candidate_routes(task_key)
        configured = [route for route in routes if PROVIDERS.get(route.provider) and PROVIDERS[route.provider].configured]
        if not configured:
            raise NonRetriableRuntimeError(
                f"no configured model provider for task '{task_key}' (candidates: {', '.join(r.provider for r in routes)})"
            )

        last_transient: Optional[Exception] = None
        for route in configured:
            provider = PROVIDERS[route.provider]
            request = request_factory(route)
            try:
                return await provider.generate(request)
            except NonRetriableRuntimeError:
                # A provider-specific authentication/setup failure does not authorize
                # us to silently switch to a different authority or billing plane.
                raise
            except (TransientRuntimeError, EmptyRuntimeResponse) as exc:
                last_transient = exc
                continue
        raise TransientRuntimeError(f"all configured candidate routes failed: {last_transient}")


agent_runtime = AgentRuntime()


def build_system_prompt(persona: AgentPersona) -> str:
    identity = persona.identity or {}
    heart = persona.heart or {}
    soul = persona.soul or {}
    skills = persona.skill_manifest or {}
    return (
        f"You are {persona.name}, the persistent Pauli's Place agent for role '{persona.role}'.\n"
        f"Specialty: {persona.specialty or 'general'}.\n"
        "Your identity persists independently of the model currently executing this request.\n"
        "Do not claim work was deployed, tested, sent, purchased, or completed unless the supplied evidence proves it.\n"
        "If required authority, tools, credentials, or evidence are missing, state BLOCKED and name the missing capability.\n"
        f"Identity context: {identity}\nHeart: {heart}\nSoul: {soul}\nSkills: {skills}"
    )


def build_task_prompt(request: RuntimeRequest) -> str:
    return (
        f"MISSION: {request.mission_title}\n"
        f"ORIGINAL INTENT: {request.mission_intent}\n"
        f"REQUESTED OUTCOME: {request.requested_outcome}\n"
        f"CURRENT TASK: {request.task_key} — {request.task_description}\n"
        f"PRIOR VERIFIED/RECORDED CONTEXT: {request.context}\n\n"
        "Return the best bounded output for this task. Distinguish facts, assumptions, blockers, and proposed next actions."
    )
