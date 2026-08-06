"""
SIX REVENUE CHANNELS — Spec §04
================================
CH1 Affiliate  (Printify + Etsy)      — profile write_long
CH2 Domains    (Namecheap/IONOS)      — profile write_short
CH3 Services   (Fiverr gigs)          — profile write_long
CH4 Micro-apps (Vercel functions)     — profile implement
CH5 Ebooks     (KDP)                   — profile write_long
CH6 Thrift     (eBay/Whatnot listings)— profile write_short

Each channel tick runs through Hermes.dispatch with OUTPUT_JUDGE gate.
Caps: $0.50/channel-run, $25/day total (override via env).
"""
from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable

from services.profile_router import call_profile
from services import hermes
from services.event_bus import build_envelope, publish


def _tick_id(channel: str) -> str:
    return f"tik_{channel}_{uuid.uuid4().hex[:12]}"


# ---- per-channel worker prompts ----

CH1_PROMPT = """You are CH1 AFFILIATE. Generate a Printify blueprint + Etsy affiliate listing for this trend.
Return JSON only:
{{
  "product_title": "<...>",
  "printify_blueprint_id": "<id>",
  "printify_print_provider_id": "<id>",
  "etsy_affiliate_url": "<listing URL>",
  "sale_price_usd": <float>,
  "blast_radius_usd": <float>
}}
TREND:
{trend_json}
"""

CH2_PROMPT = """You are CH2 DOMAINS. Pick a brandable domain from the trend keyword that we can flip or park.
Return JSON only:
{{
  "candidates": [
    {{"domain": "<text>.com", "registrar": "ionos|namecheap", "annual_cost_usd": <float>, "flip_target_usd": <float>}}
  ]
}}
TREND:
{trend_json}
"""

CH3_PROMPT = """You are CH3 SERVICES. Draft a Fiverr gig that monetizes the trend as a service.
Return JSON only:
{{
  "gig_title": "<...>",
  "category": "<...>",
  "tiers": [{{"name":"Basic","price_usd":N,"deliverables":"<...>"}}, ...],
  "estimated_hours_to_complete": <int>
}}
TREND:
{trend_json}
"""

CH4_PROMPT = """You are CH4 MICRO-APPS. Spec a tiny single-purpose web utility around the trend.
Return JSON only:
{{
  "app_name": "<slug>",
  "one_liner": "<...>",
  "spec_md": "<full markdown spec>",
  "deploy_target": "vercel",
  "monthly_run_cost_usd": <float>,
  "rent_target_usd": <float>
}}
TREND:
{trend_json}
"""

CH5_PROMPT = """You are CH5 EBOOKS. Outline a KDP manuscript outline + cover concept for the trend.
Return JSON only:
{{
  "title": "<...>",
  "subtitle": "<...>",
  "category": "<kdp category>",
  "outline_chapters": ["...", "..."],
  "cover_prompt": "<prompt>",
  "list_price_usd": <float>,
  "royalty_rate_pct": <float>
}}
TREND:
{trend_json}
"""

CH6_PROMPT = """You are CH6 THRIFT. Draft a listing for a thrift-flip item that captures the trend.
Return JSON only:
{{
  "platform": "ebay|whatnot|mercari",
  "title": "<...>",
  "category": "<...>",
  "start_bid_usd": <float>,
  "buy_now_usd": <float>,
  "condition": "used|refurb|vintage",
  "ship_from_zip": "98101",
  "human_drafting_required": true
}}
TREND:
{trend_json}
"""

_CHANNEL_CONFIG = {
    "CH1": dict(profile="write_long", services=["paulis-place", "printify", "etsy"], cap=0.50, prompt=CH1_PROMPT),
    "CH2": dict(profile="write_short", services=["paulis-place", "ionos"], cap=0.20, prompt=CH2_PROMPT),
    "CH3": dict(profile="write_long", services=["paulis-place", "fiverr"], cap=0.40, prompt=CH3_PROMPT),
    "CH4": dict(profile="implement", services=["paulis-place", "vercel"], cap=0.50, prompt=CH4_PROMPT),
    "CH5": dict(profile="write_long", services=["paulis-place", "kdp"], cap=0.50, prompt=CH5_PROMPT),
    "CH6": dict(profile="write_short", services=["paulis-place", "ebay"], cap=0.30, prompt=CH6_PROMPT),
}


async def _channel_worker(channel_id: str, trend: dict) -> dict:
    cfg = _CHANNEL_CONFIG[channel_id]
    return await call_profile(
        cfg["profile"],
        prompt=cfg["prompt"].format(trend_json=json.dumps(trend, indent=2)),
        system_prompt=f"You are {channel_id} in the Yappyverse.",
        temperature=0.4,
        max_tokens=1500,
        response_format_json=True,
    )


async def channel_tick(channel_id: str, trend: dict, expected_cost: float = 0.05) -> dict:
    """Run one channel tick through Hermes with OUTPUT_JUDGE gate."""
    cfg = _CHANNEL_CONFIG[channel_id]
    if channel_id not in _CHANNEL_CONFIG:
        raise ValueError(f"unknown channel {channel_id}")

    # L2 — channels touch ≤3 services (per spec)
    services = cfg["services"]
    if len(services) > 3:
        return await hermes._emit_halt(
            route="R-06.REVENUE.CHANNEL_TICK",
            stage="CAP_PRE_FLIGHT",
            worker_profile=cfg["profile"],
            reason=f"L2 violation: channel {channel_id} touches {len(services)} services",
        )

    tick_id = _tick_id(channel_id)
    envelope = await hermes.dispatch(
        route="R-06.REVENUE.CHANNEL_TICK",
        stage="TICK",
        services_touched=services,
        blast_radius_usd=cfg["cap"],
        worker_profile=cfg["profile"],
        worker_fn=lambda: _channel_worker(channel_id, trend),
        worker_body_builder=lambda r: {
            "tick_id": tick_id,
            "channel": channel_id,
            "output": r.get("content"),
        },
        expected_cost=expected_cost,
    )
    return envelope


# ---- Celery entrypoints (so workers.tasks.* can call these on the beat) ----

def _run_async(coro):
    """Run an async coroutine inside a celery sync task."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        # Fallback for nested loops
        from threading import Thread
        result = {}
        def _runner():
            result["v"] = loop.run_until_complete(coro)
        t = Thread(target=_runner)
        t.start(); t.join()
        return result["v"]
    return loop.run_until_complete(coro)


def ch1_tick(trend: dict) -> dict:
    return _run_async(channel_tick("CH1", trend))

def ch2_tick(trend: dict) -> dict:
    return _run_async(channel_tick("CH2", trend))

def ch3_tick(trend: dict) -> dict:
    return _run_async(channel_tick("CH3", trend))

def ch4_tick(trend: dict) -> dict:
    return _run_async(channel_tick("CH4", trend))

def ch5_tick(trend: dict) -> dict:
    return _run_async(channel_tick("CH5", trend))

def ch6_tick(trend: dict) -> dict:
    return _run_async(channel_tick("CH6", trend))


CHANNEL_DISPATCHERS = {
    "CH1": ch1_tick, "CH2": ch2_tick, "CH3": ch3_tick,
    "CH4": ch4_tick, "CH5": ch5_tick, "CH6": ch6_tick,
}