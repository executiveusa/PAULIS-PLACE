"""
SSSF Agent Roles — Spec §03
============================
5 roles, each a thin worker function:
  SCANNER     — profile=score        — R-01 SCAN  -> emits raw trend envelopes
  SCORER      — profile=score        — R-01 SCORE -> 5-axis 0-100 scoring, gates Council
  DESIGNER    — profile=write_long  — R-02 DESIGN -> artifact (printify/etsy/kdp/fiverr)
  PUBLISHER   — profile=write_short — R-02 PUBLISH -> Zernio post + lounge scene event
  RECONCILER  — profile=score       — R-05 RECONCILE -> payment reconciliation + ledger

Each function returns (output_dict, worker_model) so Hermes can judge it.
"""
from __future__ import annotations
import json
from typing import Callable, Awaitable
from services.profile_router import call_profile


SCAN_PROMPT = """You are SCANNER. Detect an emerging internet trend.
Return JSON only:
{{
  "trend_id": "trd_<slug>",
  "keyword": "<the search term>",
  "source": "google_trends|etsy_hints|tiktok_cc|amazon_movers|reddit|firecrawl",
  "velocity": <0-1 float>,
  "first_seen": "<ISO>",
  "samples": ["<url or post id>", "<url or post id>", "<url or post id>"]
}}
"""


SCORE_PROMPT = """You are SCORER. Score this trend on 5 axes (each 0-20):
- velocity, durability, margin, channel_fit, bridge_risk (20 = zero risk)
Return JSON only:
{{
  "trend_id": "<from before>",
  "scores": {{"velocity": N, "durability": N, "margin": N, "channel_fit": N, "bridge_risk": N}},
  "total": <0-100>,
  "recommended_channel": "CH1|CH2|CH3|CH4|CH5|CH6",
  "next_action": "COUNCIL_DEBATE" | "QUEUE_NEXT_CYCLE" | "DROP"
}}
TREND INPUT:
{trend_json}
"""


DESIGN_PROMPT = """You are DESIGNER. Turn this Council-approved idea into a concrete artifact spec.
Channel: {channel}. Return JSON only:
{{
  "product_id": "prd_<uuid-ish>",
  "channel": "<CH1..CH6>",
  "artifact_type": "printify_blueprint|etsy_listing|domain_bid|fiverr_gig|microapp_spec|kdp_manuscript|thrift_listing",
  "title": "<short>",
  "payload": {{ <channel-shaped artifact body, see icm/instructions/DESIGNER.md> }},
  "marketplace_target": "<printify|etsy|kdp|fiverr|...>"
}}
APPROVED IDEA:
{approved_idea}
"""


PUBLISH_PROMPT = """You are PUBLISHER. Draft the social copy for this drop.
Brand voice: Paulie's Place, Seattle 2056, jazz-lounge parody of a mob hangout. Sardonic, classy, wry.
Platforms target: {platforms_json}. 280-char-audience for X, longer for IG/Pinterest, etc.
Return JSON only:
{{
  "product_id": "<from before>",
  "posts": [
    {{"platform": "x", "text": "<280 chars>", "cta": "<link>"}},
    {{"platform": "instagram", "text": "<up to 2200 chars>", "cta": "<link>"}},
    ...
  ],
  "lounge_scene_intent": "<one sentence for Sasha to render>"
}}
PRODUCT:
{product_json}
"""


RECONCILE_PROMPT = """You are RECONCILER. Verify this payment webhook payload is legitimate and reconcile.
Return JSON only:
{{
  "payment_id": "<from payload or generated>",
  "provider": "creem|btcpay|stripe",
  "amount_usd": <float>,
  "customer_ref": "<id or null>",
  "product_id": "<prd_* or null>",
  "verified": <bool>,
  "reason": "<one line>",
  "granted_access": ["<...>"]
}}
WEBHOOK PAYLOAD:
{webhook_json}
"""


async def worker_scan(*, hint: str = "anime stickers", source: str = "firecrawl") -> dict:
    res = await call_profile("score",
        prompt=SCAN_PROMPT + f"\nHINT: {hint}\nSOURCE: {source}",
        system_prompt="You are SCANNER in the Yappyverse.",
        temperature=0.4, response_format_json=True)
    return res


async def worker_score(*, trend_envelope: dict) -> dict:
    res = await call_profile("score",
        prompt=SCORE_PROMPT.format(trend_json=json.dumps(trend_envelope, indent=2)),
        system_prompt="You are SCORER in the Yappyverse.",
        temperature=0.2, response_format_json=True)
    return res


async def worker_design(*, approved_idea: dict, channel: str = "CH1") -> dict:
    res = await call_profile("write_long",
        prompt=DESIGN_PROMPT.format(channel=channel,
                                    approved_idea=json.dumps(approved_idea, indent=2)),
        system_prompt="You are DESIGNER in the Yappyverse.",
        temperature=0.5, response_format_json=True)
    return res


async def worker_publish(*, product_json: dict, platforms: list[str] | None = None) -> dict:
    platforms = platforms or ["x", "instagram", "pinterest", "tiktok"]
    res = await call_profile("write_short",
        prompt=PUBLISH_PROMPT.format(platforms_json=json.dumps(platforms),
                                     product_json=json.dumps(product_json, indent=2)),
        system_prompt="You are PUBLISHER in the Yappyverse.",
        temperature=0.6, response_format_json=True)
    return res


async def worker_reconcile(*, webhook_payload: dict) -> dict:
    res = await call_profile("score",
        prompt=RECONCILE_PROMPT.format(webhook_json=json.dumps(webhook_payload, indent=2)),
        system_prompt="You are RECONCILER in the Yappyverse. Be paranoid.",
        temperature=0.1, response_format_json=True)
    return res


# ---- event-bus subscribers wiring each role to its inbound route-stage ----

def register_subscribers() -> None:
    """Wire SSSF workers to inbound envelopes from R-01, R-02, R-05.
    Each subscriber dispatches via Hermes so L1/L2/L3/L4 are enforced.
    """
    from services import hermes
    from services.event_bus import subscribe

    async def _scan_handler(envelope: dict) -> None:
        body = envelope.get("body", {}) or {}
        await hermes.dispatch(
            route="R-01.REVENUE.NEW_TREND", stage="SCAN",
            services_touched=["paulis-place"],
            blast_radius_usd=0.05,
            worker_profile="score",
            worker_fn=lambda: worker_scan(hint=body.get("hint", "anime stickers"),
                                          source=body.get("source", "firecrawl")),
            worker_body_builder=lambda r: {"scan_output": r.get("content")},
            expected_cost=0.02,
        )

    async def _score_handler(envelope: dict) -> None:
        body = envelope.get("body", {}) or {}
        trend = body if "keyword" in body else body.get("scan_output", body)
        await hermes.dispatch(
            route="R-01.REVENUE.NEW_TREND", stage="SCORE",
            services_touched=["paulis-place"],
            blast_radius_usd=0.05,
            worker_profile="score",
            worker_fn=lambda: worker_score(trend_envelope=trend),
            worker_body_builder=lambda r: {"score_output": r.get("content")},
            expected_cost=0.02,
        )

    async def _design_handler(envelope: dict) -> None:
        body = envelope.get("body", {}) or {}
        await hermes.dispatch(
            route="R-02.REVENUE.PRODUCT_CREATED", stage="DESIGN",
            services_touched=["paulis-place"],
            blast_radius_usd=0.10,
            worker_profile="write_long",
            worker_fn=lambda: worker_design(approved_idea=body,
                                             channel=body.get("recommended_channel", "CH1")),
            worker_body_builder=lambda r: {"design_output": r.get("content")},
            expected_cost=0.08,
        )

    async def _publish_handler(envelope: dict) -> None:
        body = envelope.get("body", {}) or {}
        prod = body.get("design_output") or body
        await hermes.dispatch(
            route="R-02.REVENUE.PRODUCT_CREATED", stage="PUBLISH",
            services_touched=["paulis-place", "zernio"],
            blast_radius_usd=0.05,
            worker_profile="write_short",
            worker_fn=lambda: worker_publish(product_json=prod),
            worker_body_builder=lambda r: {"publish_output": r.get("content")},
            expected_cost=0.04,
        )

    async def _reconcile_handler(envelope: dict) -> None:
        body = envelope.get("body", {}) or {}
        await hermes.dispatch(
            route="R-05.PAYMENT.SETTLED", stage="RECONCILE",
            services_touched=["paulis-place", "creem"],
            blast_radius_usd=0.05,
            worker_profile="score",
            worker_fn=lambda: worker_reconcile(webhook_payload=body),
            worker_body_builder=lambda r: {"reconcile_output": r.get("content")},
            expected_cost=0.02,
        )

    subscribe("R-01.REVENUE.NEW_TREND.SCAN", _scan_handler)
    subscribe("R-01.REVENUE.NEW_TREND.SCORE", _score_handler)
    subscribe("R-02.REVENUE.PRODUCT_CREATED.DESIGN", _design_handler)
    subscribe("R-02.REVENUE.PRODUCT_CREATED.PUBLISH", _publish_handler)
    subscribe("R-05.PAYMENT.SETTLED.RECONCILE", _reconcile_handler)