"""
LEDGER MODEL & SERVICE — Spec §06
=================================
Double-entry-style ledger. Every webhook that resolves to PAID creates:
  - 1 Payment row (DB)            — already exists in payment_service
  - 1 LedgerEntry row              — NEW: spec payment_ledger table
  - 1 R-05.R... LEDGER envelope   — published to event_bus
  - 1 R-05 R... CELEBRATE event   — for the 3D lounge to render

Replaces the legacy handlers with spec-compliant ones that route through Hermes.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import json

from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Float, Boolean, ForeignKey

from models.base import Base, SessionLocal
from services import hermes
from services.event_bus import build_envelope, publish


class LedgerEntry(Base):
    """Immutable append-only ledger. One row per single economic event."""
    __tablename__ = "yappy_ledger"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(String(100), unique=True, index=True)  # led_<uuid>
    ts = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    debit_account = Column(String(120), index=True)   # source / revenue channel
    credit_account = Column(String(120), index=True)  # destination / bank
    amount_usd = Column(Float, default=0.0)
    kind = Column(String(60), index=True)  # "revenue" | "cost" | "payout" | "refund"
    payment_id = Column(String(120), nullable=True, index=True)
    product_id = Column(String(120), nullable=True, index=True)
    envelope_ref = Column(String(120), nullable=True, index=True)
    entry_metadata = Column("entry_metadata", JSON, default=dict)

    def to_dict(self):
        return {
            "entry_id": self.entry_id,
            "ts": self.ts.isoformat() if self.ts else None,
            "debit_account": self.debit_account,
            "credit_account": self.credit_account,
            "amount_usd": self.amount_usd,
            "kind": self.kind,
            "payment_id": self.payment_id,
            "product_id": self.product_id,
            "envelope_ref": self.envelope_ref,
            "metadata": self.entry_metadata,
        }


def write_ledger_entry(
    *,
    entry_id: str,
    kind: str,
    debit_account: str,
    credit_account: str,
    amount_usd: float,
    payment_id: Optional[str] = None,
    product_id: Optional[str] = None,
    envelope_ref: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    db = SessionLocal()
    try:
        entry = LedgerEntry(
            entry_id=entry_id, kind=kind,
            debit_account=debit_account, credit_account=credit_account,
            amount_usd=amount_usd,
            payment_id=payment_id, product_id=product_id,
            envelope_ref=envelope_ref,
            entry_metadata=metadata or {},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry.to_dict()
    finally:
        db.close()


async def reconcile_event(*, payment_id: str, provider: str, amount_usd: float,
                          customer_ref: Optional[str] = None,
                          product_id: Optional[str] = None,
                          granted_access: Optional[list[str]] = None) -> dict:
    """Run R-05 RECONCILE -> LEDGER -> CELEBRATE."""
    worker_fn = _run_reconcile_worker(provider, amount_usd, customer_ref, product_id)
    envelope = await hermes.dispatch(
        route="R-05.PAYMENT.SETTLED",
        stage="RECONCILE",
        services_touched=["paulis-place", provider],
        blast_radius_usd=0.05,
        worker_profile="score",
        worker_fn=worker_fn,
        worker_body_builder=lambda r: {"reconcile_output": r.get("content")},
        expected_cost=0.02,
    )
    if envelope.get("judge_verdict") != "accept":
        return envelope

    reconcile_output = envelope.get("body", {}).get("reconcile_output", {}) or {}
    if not reconcile_output.get("verified"):
        # Don't progress to LEDGER/Celebrate if not verified
        return envelope

    # LEDGER entry (L2 — touches 2 services: paulis-place + provider)
    from services.event_bus import new_event_id
    ledger_entry = write_ledger_entry(
        entry_id=f"led_{new_event_id().replace('evt_','')}",
        kind="revenue",
        debit_account=provider,
        credit_account="paulis_place_operating",
        amount_usd=float(amount_usd),
        payment_id=payment_id,
        product_id=product_id,
        envelope_ref=envelope["event_id"],
        metadata={"customer_ref": customer_ref,
                  "granted_access": granted_access or []},
    )

    ledger_env = build_envelope(
        route="R-05.PAYMENT.SETTLED", stage="LEDGER",
        services_touched=["paulis-place"],
        blast_radius_usd=0.0,
        worker_profile="score", worker_model="ledger_writer",
        body={"ledger_entry": ledger_entry, "granted_access": granted_access or []},
        judge_verdict="accept", judge_model="ledger_writer",
        next_action="CELEBRATE",
    )
    await publish(ledger_env)

    # CELEBRATE — emit ilişkili scene request
    celeb_env = build_envelope(
        route="R-05.PAYMENT.SETTLED", stage="CELEBRATE",
        services_touched=["paulis-place"],
        blast_radius_usd=0.0,
        worker_profile="write_short", worker_model="lounge_celebration",
        body={
            "payment_id": payment_id,
            "amount_usd": float(amount_usd),
            "product_id": product_id,
            "celebration_intent": "open a bottle",
            "avatars": [{"id":"av_paulie","action":"celebrate",
                         "line": f"${amount_usd:.2f} just walked in the door, kid."}],
        },
        judge_verdict="accept", judge_model="lounge_celebration",
        next_action="LOUNGE_RENDER",
    )
    await publish(celeb_env)

    return {"reconcile": envelope, "ledger": ledger_env, "celebrate": celeb_env}


def _run_reconcile_worker(provider, amount_usd, customer_ref, product_id):
    """Build the async worker_fn for Hermes.dispatch-over-the-reconcile profile."""
    async def _fn():
        from agents.sssf import worker_reconcile
        return await worker_reconcile(webhook_payload={
            "provider": provider,
            "amount_usd": amount_usd,
            "customer_ref": customer_ref,
            "product_id": product_id,
        })
    return _fn