from datetime import datetime, timedelta, timezone

from services.business_intelligence import build_owner_brief, build_snapshot, summarize_economic_events


NOW = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)


def test_missing_financial_coverage_is_unknown_not_zero():
    money = summarize_economic_events([], now=NOW)
    assert money["coverage"] == "missing"
    assert money["revenue_cents"] is None
    assert money["profit_cents"] is None


def test_profit_arithmetic_uses_revenue_minus_cost_fee_and_refund():
    events = [
        {"kind": "revenue", "amount_cents": 10000, "occurred_at": NOW},
        {"kind": "cost", "amount_cents": 2500, "occurred_at": NOW},
        {"kind": "fee", "amount_cents": 500, "occurred_at": NOW},
        {"kind": "refund", "amount_cents": 1000, "occurred_at": NOW},
        {"kind": "payout", "amount_cents": 6000, "occurred_at": NOW},
    ]
    money = summarize_economic_events(events, now=NOW)
    assert money["revenue_cents"] == 10000
    assert money["profit_cents"] == 6000
    assert money["payout_cents"] == 6000


def test_old_financial_events_are_marked_stale():
    old = NOW - timedelta(hours=30)
    money = summarize_economic_events([{"kind": "revenue", "amount_cents": 100, "occurred_at": old}], now=NOW, stale_after_hours=24)
    assert money["coverage"] == "stale"


def test_owner_brief_cites_missing_money_and_pending_owner_approval():
    snapshot = build_snapshot(
        economic_events=[],
        pod_operations=[{"status": "published"}],
        software_operations=[{"status": "preview_ready"}],
        digital_operations=[{"status": "listing_draft_ready"}],
        approvals=[{"status": "pending"}],
        agents=[{"status": "working"}],
        now=NOW,
    )
    brief = build_owner_brief(snapshot)
    assert brief["outcome"]["revenue_cents"] is None
    assert brief["decisions"][0]["action"] == "reconcile_financial_sources"
    assert brief["needs_you"][0]["count"] == 1
    assert brief["evidence"][0]["source_hash"] == snapshot.source_hash


def test_negative_profit_creates_evidence_backed_cost_review_decision():
    snapshot = build_snapshot(
        economic_events=[
            {"kind": "revenue", "amount_cents": 1000, "occurred_at": NOW},
            {"kind": "cost", "amount_cents": 1500, "occurred_at": NOW},
        ],
        pod_operations=[], software_operations=[], digital_operations=[], approvals=[], agents=[], now=NOW,
    )
    brief = build_owner_brief(snapshot)
    decision = next(item for item in brief["decisions"] if item["action"] == "review_cost_refund_drivers")
    assert "money.profit_cents" in decision["evidence"]
    assert brief["outcome"]["profit_cents"] == -500


def test_phase7_schema_is_tenant_scoped_and_source_qualified():
    path = "backend/supabase/migrations/20260827_pauli_business_intelligence.sql"
    with open(path, "r", encoding="utf-8") as handle:
        sql = handle.read()
    assert "pauli.economic_events" in sql
    assert "organization_id uuid not null" in sql
    assert "coverage_status" in sql
    assert "source_hash" in sql
    assert "owner_briefs" in sql
