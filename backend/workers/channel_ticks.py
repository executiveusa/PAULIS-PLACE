"""Celery task wrappers for the six revenue channels + nightly self-improve.
Bridges sync Celery → async channel ticks.
"""
from __future__ import annotations
from workers.celery_app import app
from channels import CHANNEL_DISPATCHERS, _run_async
import asyncio


def _synthetic_trend_for(channel_id: str) -> dict:
    """Generate or load the latest council-approved trend for a channel.
       For MVP, returns a placeholder trend so the channel still ticks.
       Production should query the latest APPROVE ruling from icm/memory/decisions/.
    """
    return {
        "trend_id": f"trd_synth_{channel_id.lower()}",
        "keyword": "Seattle 2056 jazz lounge merch",
        "source": "council_approved_pool",
        "niche": "lifestyle",
        "channel_hint": channel_id,
    }


def _make_tick(chid: str):
    @app.task(name=f"workers.channel_ticks.{chid.lower()}_tick_task")
    def _t():
        trend = _synthetic_trend_for(chid)
        return _run_async(CHANNEL_DISPATCHERS[chid](trend))
    return _t


ch1_tick_task = _make_tick("CH1")
ch2_tick_task = _make_tick("CH2")
ch3_tick_task = _make_tick("CH3")
ch4_tick_task = _make_tick("CH4")
ch5_tick_task = _make_tick("CH5")
ch6_tick_task = _make_tick("CH6")


@app.task(name="workers.channel_ticks.self_improve_task")
def self_improve_task():
    """Nightly self-improvement loop (spec §09). Will be implemented by subsystem 09."""
    # Late import to keep this module standalone-safe
    try:
        from agents.self_improve import run_nightly
        return _run_async(run_nightly())
    except Exception as e:
        print(f"[self_improve] not yet wired: {e}")
        return {"status": "pending_subsystem_09"}