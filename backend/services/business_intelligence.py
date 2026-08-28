"""Source-qualified business intelligence for Pauli's Place.

The owner layer never turns missing financial coverage into a fabricated zero.
Money comes from tenant-scoped ``pauli.economic_events``; operational state comes
from the governed POD/software/digital-product ledgers and canonical approvals.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import text

from services.capability_guard import redact_secrets


class BusinessIntelligenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class MetricSnapshot:
    metrics: dict[str, Any]
    coverage_status: str
    provenance: list[dict[str, Any]]
    source_hash: str
    as_of: datetime


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(redact_secrets(payload), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        result = value
    else:
        try:
            result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def summarize_economic_events(
    events: Iterable[dict[str, Any]], *, now: datetime | None = None, stale_after_hours: int = 24
) -> dict[str, Any]:
    rows = [dict(row) for row in events]
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not rows:
        return {
            "coverage": "missing",
            "as_of": None,
            "revenue_cents": None,
            "cost_cents": None,
            "fee_cents": None,
            "refund_cents": None,
            "profit_cents": None,
            "payout_cents": None,
            "event_count": 0,
        }

    totals = {"revenue": 0, "cost": 0, "fee": 0, "refund": 0, "payout": 0}
    timestamps: list[datetime] = []
    for row in rows:
        kind = str(row.get("kind") or "")
        if kind not in totals:
            raise BusinessIntelligenceError(f"Unknown economic event kind: {kind}")
        amount = int(row.get("amount_cents", -1))
        if amount < 0:
            raise BusinessIntelligenceError("Economic event amounts must be non-negative cents")
        totals[kind] += amount
        timestamp = _dt(row.get("occurred_at"))
        if timestamp:
            timestamps.append(timestamp)

    latest = max(timestamps) if timestamps else None
    coverage = "complete"
    if latest is None:
        coverage = "partial"
    elif (now - latest).total_seconds() > max(1, int(stale_after_hours)) * 3600:
        coverage = "stale"

    return {
        "coverage": coverage,
        "as_of": latest.isoformat() if latest else None,
        "revenue_cents": totals["revenue"],
        "cost_cents": totals["cost"],
        "fee_cents": totals["fee"],
        "refund_cents": totals["refund"],
        "profit_cents": totals["revenue"] - totals["cost"] - totals["fee"] - totals["refund"],
        "payout_cents": totals["payout"],
        "event_count": len(rows),
    }


def _count_status(rows: Iterable[dict[str, Any]], statuses: set[str]) -> int:
    return sum(1 for row in rows if str(row.get("status") or "") in statuses)


def build_snapshot(
    *,
    economic_events: list[dict[str, Any]],
    pod_operations: list[dict[str, Any]],
    software_operations: list[dict[str, Any]],
    digital_operations: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    agents: list[dict[str, Any]],
    now: datetime | None = None,
    stale_after_hours: int = 24,
) -> MetricSnapshot:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    money = summarize_economic_events(economic_events, now=now, stale_after_hours=stale_after_hours)

    pod = [dict(x) for x in pod_operations]
    software = [dict(x) for x in software_operations]
    digital = [dict(x) for x in digital_operations]
    approval_rows = [dict(x) for x in approvals]
    agent_rows = [dict(x) for x in agents]

    metrics = {
        "money": money,
        "products": {
            "pod_total": len(pod),
            "pod_published": _count_status(pod, {"published"}),
            "digital_total": len(digital),
            "digital_sell_ready": _count_status(digital, {"listing_draft_ready", "waiting_publish_approval", "published"}),
            "digital_published": _count_status(digital, {"published"}),
        },
        "software": {
            "total": len(software),
            "preview_ready": _count_status(software, {"preview_ready", "waiting_production_approval", "production_deployed"}),
            "production_deployed": _count_status(software, {"production_deployed"}),
        },
        "work": {
            "failed_or_repairing": _count_status(pod, {"failed", "blocked"})
            + _count_status(software, {"failed", "blocked", "repairing", "tests_failed"})
            + _count_status(digital, {"failed", "blocked", "repairing"}),
            "pending_approvals": _count_status(approval_rows, {"pending"}),
            "agents_working": _count_status(agent_rows, {"working", "meeting", "recovering"}),
            "agents_blocked": _count_status(agent_rows, {"blocked", "error", "waiting_approval"}),
        },
    }

    provenance = [
        {"source": "pauli.economic_events", "rows": len(economic_events), "as_of": money["as_of"], "coverage": money["coverage"]},
        {"source": "pauli.commerce_operations", "rows": len(pod)},
        {"source": "pauli.software_operations", "rows": len(software)},
        {"source": "pauli.digital_product_operations", "rows": len(digital)},
        {"source": "pauli.approvals", "rows": len(approval_rows)},
        {"source": "pauli.agents", "rows": len(agent_rows)},
    ]
    coverage = money["coverage"]
    source_hash = canonical_hash({"metrics": metrics, "provenance": provenance})
    return MetricSnapshot(metrics=metrics, coverage_status=coverage, provenance=provenance, source_hash=source_hash, as_of=now)


def build_owner_brief(snapshot: MetricSnapshot) -> dict[str, Any]:
    money = snapshot.metrics["money"]
    work = snapshot.metrics["work"]
    products = snapshot.metrics["products"]
    software = snapshot.metrics["software"]

    outcome = {
        "coverage_status": snapshot.coverage_status,
        "as_of": snapshot.as_of.isoformat(),
        "revenue_cents": money["revenue_cents"],
        "cost_cents": money["cost_cents"],
        "profit_cents": money["profit_cents"],
        "pod_published": products["pod_published"],
        "digital_sell_ready": products["digital_sell_ready"],
        "software_preview_ready": software["preview_ready"],
    }

    decisions: list[dict[str, Any]] = []
    if snapshot.coverage_status == "missing":
        decisions.append({
            "priority": 100,
            "action": "reconcile_financial_sources",
            "reason": "Tenant-scoped financial coverage is missing; revenue/profit are unknown, not zero.",
            "evidence": ["money.coverage"],
        })
    elif snapshot.coverage_status == "stale":
        decisions.append({
            "priority": 95,
            "action": "refresh_financial_sources",
            "reason": "Financial data is stale; do not make scaling decisions from the current snapshot.",
            "evidence": ["money.as_of", "money.coverage"],
        })
    elif money["profit_cents"] is not None and money["profit_cents"] < 0:
        decisions.append({
            "priority": 90,
            "action": "review_cost_refund_drivers",
            "reason": "Verified profit is negative for the covered economic events.",
            "evidence": ["money.profit_cents", "money.cost_cents", "money.refund_cents", "money.fee_cents"],
        })
    elif money["profit_cents"] is not None and money["profit_cents"] > 0:
        decisions.append({
            "priority": 60,
            "action": "inspect_verified_winners_for_scale",
            "reason": "The covered economic events show positive profit; scale only products with attributable evidence.",
            "evidence": ["money.profit_cents", "products.pod_published", "products.digital_published"],
        })

    if work["failed_or_repairing"]:
        decisions.append({
            "priority": 85,
            "action": "repair_failed_operations",
            "reason": "One or more governed operations are failed, blocked, or repairing.",
            "evidence": ["work.failed_or_repairing"],
        })

    needs_you = []
    if work["pending_approvals"]:
        needs_you.append({
            "type": "approval",
            "count": work["pending_approvals"],
            "summary": "Consequential actions are waiting for owner approval.",
            "evidence": ["work.pending_approvals"],
        })

    working_now = [{"type": "agents", "count": work["agents_working"], "blocked": work["agents_blocked"]}]
    evidence = [{"source_hash": snapshot.source_hash, "provenance": snapshot.provenance}]
    decisions.sort(key=lambda item: item["priority"], reverse=True)
    brief = {"outcome": outcome, "decisions": decisions, "evidence": evidence, "needs_you": needs_you, "working_now": working_now}
    return {**brief, "brief_hash": canonical_hash(brief)}


class BusinessIntelligenceService:
    def collect(self, db, *, organization_id: str, stale_after_hours: int = 24) -> MetricSnapshot:
        params = {"org": organization_id}
        economic = db.execute(text("select provider,external_ref,kind,amount_cents,currency,product_ref,source_ref,evidence,occurred_at from pauli.economic_events where organization_id=:org order by occurred_at"), params).mappings().all()
        pod = db.execute(text("select id,status,printify_product_id,etsy_listing_id,completed_at,updated_at from pauli.commerce_operations where organization_id=:org"), params).mappings().all()
        software = db.execute(text("select id,status,repository_full_name,branch_ref,commit_sha,preview_url,completed_at,updated_at from pauli.software_operations where organization_id=:org"), params).mappings().all()
        digital = db.execute(text("select id,status,product_key,product_type,package_sha256,distribution_ref,completed_at,updated_at from pauli.digital_product_operations where organization_id=:org"), params).mappings().all()
        approvals = db.execute(text("select id,status,action_class,risk_class,created_at,decided_at from pauli.approvals where organization_id=:org"), params).mappings().all()
        agents = db.execute(text("select id,agent_key,status,last_heartbeat_at from pauli.agents where organization_id=:org"), params).mappings().all()
        return build_snapshot(
            economic_events=[dict(x) for x in economic], pod_operations=[dict(x) for x in pod],
            software_operations=[dict(x) for x in software], digital_operations=[dict(x) for x in digital],
            approvals=[dict(x) for x in approvals], agents=[dict(x) for x in agents], stale_after_hours=stale_after_hours,
        )

    def persist(self, db, *, organization_id: str, snapshot_key: str, snapshot: MetricSnapshot) -> dict[str, Any]:
        row = db.execute(text("""
            insert into pauli.business_metric_snapshots(
              organization_id,snapshot_key,as_of,coverage_status,metrics,provenance,source_hash
            ) values(:org,:key,:as_of,:coverage,cast(:metrics as jsonb),cast(:provenance as jsonb),:hash)
            on conflict (organization_id,snapshot_key,source_hash) do update set as_of=excluded.as_of
            returning id::text
        """), {"org": organization_id, "key": snapshot_key, "as_of": snapshot.as_of,
                "coverage": snapshot.coverage_status, "metrics": json.dumps(snapshot.metrics),
                "provenance": json.dumps(snapshot.provenance), "hash": snapshot.source_hash}).scalar_one()
        brief = build_owner_brief(snapshot)
        db.execute(text("""
            insert into pauli.owner_briefs(
              organization_id,snapshot_id,brief_hash,outcome,decisions,evidence,needs_you,working_now
            ) values(:org,cast(:snapshot as uuid),:hash,cast(:outcome as jsonb),cast(:decisions as jsonb),
              cast(:evidence as jsonb),cast(:needs as jsonb),cast(:working as jsonb))
            on conflict (snapshot_id,brief_hash) do nothing
        """), {"org": organization_id, "snapshot": row, "hash": brief["brief_hash"],
                "outcome": json.dumps(brief["outcome"]), "decisions": json.dumps(brief["decisions"]),
                "evidence": json.dumps(brief["evidence"]), "needs": json.dumps(brief["needs_you"]),
                "working": json.dumps(brief["working_now"])})
        db.commit()
        return {"snapshot_id": row, **brief}


business_intelligence_service = BusinessIntelligenceService()
