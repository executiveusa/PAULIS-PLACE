# PUBLISHER — Zernio + Lounge Broadcast Agent

> File: `icm/instructions/PUBLISHER.md`
> Route: R-02 · REVENUE.PRODUCT_CREATED (output side) + R-05 · PAYMENT.SETTLED
> Owner: `backend/services/zernio_service.py` + `backend/agents/publisher_agent.py`

## 0. Purpose
After a product is approved and (if needed) human-approved, the Publisher broadcasts it across Zernio's 15+ platforms, and simultaneously fires a LOUNGE_SCENE event so the 3D world reflects the new drop.

## 1. Zernio platforms (default set, configurable)
X, Facebook, Instagram, LinkedIn, Pinterest, TikTok, YouTube Shorts, Reddit, Bluesky, Threads, Mastodon, Telegram channel, Discord, Threads, Threads, Dev.to, Medium.

Zernio key: `ZERNIO_API_TOKEN`. Auth flow = single browser click (spec 05 section 3).

## 2. Output envelope
```json
{
  "event_id": "evt_<uuid>",
  "route": "R-02.REVENUE.PRODUCT_CREATED",
  "stage": "PUBLISH",
  "product_id": "prd_<uuid>",
  "platforms_attempted": ["x","instagram","pinterest","tiktok"],
  "platforms_succeeded": ["x","instagram","pinterest"],
  "platforms_failed": [{"platform":"tiktok","reason":"..."}],
  "post_urls": {"x":"https://...","instagram":"https://..."},
  "lounge_scene_id": "scn_<uuid>"
}
```

## 3. STYLE_JUDGE gate
Every Zernio post copy goes through a STYLE_JUDGE pass before send:
- Profile `judge` (claude-fable-5 / glm-4.6 high-thinking)
- Checks: brand voice (Paulie's Place 2056 jazz-lounge parody), no spam patterns, no banned phrases, nother-confessional "AI made this" disclosure per platform ToS
- Verdict `reject` → fixes loop. Verdict `halt` → human review.

## 4. Limits
- Per-post cost ≤ $0.02 (write_short profile: grok-4.5 / glm-5.2 fast)
- No re-posts within 24h of the same product on the same platform.
- No bulk deletes — fixes go throughSTYLE_JUDGE + human.