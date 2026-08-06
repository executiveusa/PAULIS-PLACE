# SCANNER — Trend Detection Agent

> File: `icm/instructions/SCANNER.md`
> Route: R-01 · REVENUE.NEW_TREND (split into scan + score)
> Owner: `backend/agents/research_agent.py` + `backend/workers/tasks.py::scan_all_trends`

## 0. Purpose
Detect emerging trends across Google Trends, Etsy hint pages, TikTok Creative Center, Amazon Movers & Shakers, Reddit r/BuyItForLife + r/ProductPorn. Output raw trend envelopes to the queue.

## 1. Inputs
- Google Trends via pytrends (no API key, needs proxy at scale; `TRENDS_PROXY`)
- Firecrawl for raw page extraction (`FIRECRAWL_API_TOKEN`)
- Apify for TikTok/Reddit scrapes (`APIFY_API_KEY`)

## 2. Output envelope (emitted to event bus)
```json
{
  "event_id": "evt_<uuid>",
  "route": "R-01.REVENUE.NEW_TREND",
  "stage": "SCAN",
  "trend_id": "trd_<slug>",
  "keyword": "<text>",
  "source": "google_trends" | "etsy_hints" | "tiktok_cc" | "amazon_movers" | "reddit",
  "velocity": <float, 0-1>,
  "first_seen": "<ISO>",
  "samples": [<3 sample URLs or post IDs>]
}
```

## 3. Hard limits
- Max 200 trends per scan cycle.
- Each scan worker is profile `score` (qwen-3.5 / llama-70b) for cheap numerical work.
- Scan cost ≤ $0.05 per cycle.
- Never write to external services. Read-only.

## 4. Forbidden
- No hallucinated trends. Every trend must have a source URL or post ID.
- No personal data collection. No auth-walled scraping.