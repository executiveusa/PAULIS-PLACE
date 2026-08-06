# SCORER — Trend Scoring Agent

> File: `icm/instructions/SCORER.md`
> Route: R-01 · REVENUE.NEW_TREND (after Scanner)
> Owner: `backend/agents/idea_factory.py` + `backend/workers/tasks.py::score_hot_trends`

## 0. Purpose
Take raw trend envelopes from the Scanner, score them on a 0-100 across 5 axes, surface the top 5 to Council for debate. Top survivors get product proposals.

## 1. The 5 scoring axes (each 0-20)
- **Velocity** — how fast the trend is rising
- **Durability** — how long it's likely to stay hot (fads vs evergreen)
- **Margin** — likely gross margin if we ship a product (Printify, Etsy, KDP, Fiverr)
- **Channel_fit** — matches one of our 6 channels (CH1 affiliate / CH2 domains / CH3 services / CH4 micro-apps / CH5 ebooks / CH6 thrift)
- **Bridge_risk** — inverse: legal/ToS/brand-risk exposure (20 = zero risk, 0 = certain takedown)

Total ≥ 65 → route to Council. 50–64 → queue for next cycle. < 50 → drop.

## 2. Output envelope (to COUNCIL.DEBATE_REQUEST)
```json
{
  "event_id": "evt_<uuid>",
  "route": "R-01.REVENUE.NEW_TREND",
  "stage": "SCORE",
  "trend_id": "trd_<slug>",
  "scores": {"velocity": 18, "durability": 12, "margin": 15, "channel_fit": 17, "bridge_risk": 19},
  "total": 81,
  "recommended_channel": "CH1" | "CH2" | "CH3" | "CH4" | "CH5" | "CH6",
  "scorer_model": "<model id>",
  "next_action": "COUNCIL_DEBATE"
}
```

## 3. Limits
- Profile `score` (qwen-3.5 / llama-3.1-70b via OpenRouter) — cheap numerical reasoning.
- Per-trend cost ≤ $0.01. Batch scoring only.
- No contradictory resets — once a trend is dropped < 50, it's dropped for 24h.