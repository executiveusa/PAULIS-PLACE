"""Fail-closed execution policy for pauli-runtime-v1.

This module is intentionally provider-agnostic. The runtime receives only a
redacted execution contract and refuses work when capabilities, approvals, or
budgets do not authorize the requested action.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SAFE = "SAFE"
CAUTION = "CAUTION"
DANGEROUS = "DANGEROUS"
CRITICAL = "CRITICAL"
CONSEQUENTIAL = {CAUTION, DANGEROUS, CRITICAL}

SECRET_MARKERS = ("secret", "token", "password", "api_key", "apikey", "authorization", "private_key")


@dataclass(frozen=True)
class CapabilityDecision:
    allowed: bool
    reason: str
    risk_class: str
    required: tuple[str, ...]
    granted: tuple[str, ...]
    estimated_spend_cents: int

    def receipt(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "risk_class": self.risk_class,
            "required_capabilities": list(self.required),
            "granted_capabilities": list(self.granted),
            "estimated_spend_cents": self.estimated_spend_cents,
        }


def redact(value: Any) -> Any:
    """Recursively remove likely secret values before logging/evidence."""
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            output[key] = "[REDACTED]" if any(marker in lowered for marker in SECRET_MARKERS) else redact(item)
        return output
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return value


def evaluate_execution(*, required_capabilities: list[str], contract: dict[str, Any]) -> CapabilityDecision:
    required = tuple(sorted(set(required_capabilities)))
    granted = tuple(sorted(set(str(x) for x in contract.get("granted_capabilities", []) if str(x).strip())))
    revoked = set(str(x) for x in contract.get("revoked_capabilities", []) if str(x).strip())
    risk = str(contract.get("risk_class", SAFE)).upper()
    if risk not in {SAFE, CAUTION, DANGEROUS, CRITICAL}:
        return CapabilityDecision(False, "invalid_risk_class", risk, required, granted, 0)

    missing = sorted(set(required) - set(granted))
    if missing:
        return CapabilityDecision(False, f"missing_capability:{','.join(missing)}", risk, required, granted, 0)

    revoked_required = sorted(set(required) & revoked)
    if revoked_required:
        return CapabilityDecision(False, f"revoked_capability:{','.join(revoked_required)}", risk, required, granted, 0)

    approval = contract.get("approval") or {}
    if risk in CONSEQUENTIAL and approval.get("status") != "approved":
        return CapabilityDecision(False, "persisted_approval_required", risk, required, granted, 0)

    estimated = max(0, int(contract.get("estimated_spend_cents", 0) or 0))
    mission_remaining = max(0, int(contract.get("mission_remaining_budget_cents", 0) or 0))
    action_ceiling = max(0, int(contract.get("action_spend_ceiling_cents", mission_remaining) or 0))
    if estimated > mission_remaining:
        return CapabilityDecision(False, "mission_budget_exceeded", risk, required, granted, estimated)
    if estimated > action_ceiling:
        return CapabilityDecision(False, "action_spend_ceiling_exceeded", risk, required, granted, estimated)

    return CapabilityDecision(True, "authorized", risk, required, granted, estimated)
