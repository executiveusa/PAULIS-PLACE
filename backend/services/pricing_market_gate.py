"""Fail-closed client for Terabithia Pricing Intelligence.

Pauli's Place may propose pricing, but it cannot approve its own pricing.
This module requests an authoritative decision from Terabithia and blocks
market-ready pricing when the control plane is unavailable or unverified.
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class PricingGateError(RuntimeError):
    pass


class PricingGateBlocked(PricingGateError):
    pass


ALLOWED_GATES = {"PRICING_PASS", "PRICING_CONDITIONAL", "PRICING_FAIL"}
METHODOLOGY_VERSION = "pricing-market-gate-v1"


def _config() -> tuple[str, str]:
    base_url = os.environ.get("TERABITHIA_PRICING_URL", "").strip().rstrip("/")
    api_key = os.environ.get("TERABITHIA_API_KEY", "").strip()
    if not base_url or not api_key:
        raise PricingGateBlocked(
            "BLOCKED — UNVERIFIED PRICING: TERABITHIA_PRICING_URL and TERABITHIA_API_KEY are required."
        )
    return base_url, api_key


def _validate_decision(payload: dict[str, Any]) -> dict[str, Any]:
    required = {
        "decision_id",
        "product_id",
        "segment_id",
        "minimum_viable_price",
        "confidence_score",
        "gate",
        "methodology_version",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise PricingGateBlocked(f"BLOCKED — UNVERIFIED PRICING: decision missing {', '.join(missing)}")

    if payload["gate"] not in ALLOWED_GATES:
        raise PricingGateBlocked("BLOCKED — UNVERIFIED PRICING: unknown gate status")
    if payload["methodology_version"] != METHODOLOGY_VERSION:
        raise PricingGateBlocked("BLOCKED — UNVERIFIED PRICING: unsupported methodology version")

    score = payload["confidence_score"]
    if not isinstance(score, (int, float)) or score < 0 or score > 100:
        raise PricingGateBlocked("BLOCKED — UNVERIFIED PRICING: invalid confidence score")

    # A factory never upgrades a conditional/fail response locally.
    return payload


async def evaluate_pricing(request_payload: dict[str, Any]) -> dict[str, Any]:
    """Request a fresh pricing decision from Terabithia."""
    base_url, api_key = _config()
    url = f"{base_url}/api/v1/pricing/evaluate"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Pricing-Consumer": "paulis-place",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=request_payload, headers=headers)
    except httpx.HTTPError as exc:
        raise PricingGateBlocked("BLOCKED — UNVERIFIED PRICING: Terabithia pricing service unavailable") from exc

    if response.status_code != 200:
        raise PricingGateBlocked(
            f"BLOCKED — UNVERIFIED PRICING: Terabithia rejected request ({response.status_code})"
        )

    data = response.json()
    if not isinstance(data, dict):
        raise PricingGateBlocked("BLOCKED — UNVERIFIED PRICING: malformed Terabithia response")
    return _validate_decision(data)


def authorize_public_pricing(decision: dict[str, Any]) -> dict[str, Any]:
    """Enforce the hard launch gate before public pricing/billing actions."""
    decision = _validate_decision(decision)
    if decision["gate"] != "PRICING_PASS" or decision["confidence_score"] < 85:
        raise PricingGateBlocked(
            f"BLOCKED — UNVERIFIED PRICING: gate={decision['gate']} confidence={decision['confidence_score']}"
        )
    return decision
