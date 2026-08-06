# EVENT BUS — Routes & Envelopes

> File: `icm/context/EVENT_BUS.md`
> Backbone: Redis pub/sub (`redis://redis:6379/0`) + WebSocket fan-out to 3D lounge.

## 1. The seven routes
| Route ID | Trigger | Hermes stage | Workers |
|---|---|---|---|
| R-01 | REVENUE.NEW_TREND (cron 4x daily) | plan → scan → score → council | SCANNER, SCORER, ADVOCATE, CRITIC, JUDGE |
| R-02 | REVENUE.PRODUCT_CREATED (post-Council APPROVE) | plan → design → publish → lounge | DESIGNER, PUBLISHER, STYLE_JUDGE, LOUNGE_SCENE |
| R-03 | COUNCIL.DEBATE_REQUEST (any agent proposing) | plan → debate → lock | ADVOCATE, CRITIC, JUDGE |
| R-04 | WORLD.HUMAN_VOICE_COMMAND (browser voice) | plan → route → safe-check → avatar → reaction | SAFETY_JUDGE, nearest AVATAR |
| R-05 | PAYMENT.SETTLED (Creem + BTCPay webhooks) | plan → reconcile → ledger → celebrate | RECONCILER, LEDGER, LOUNGE_CELEBRATION |
| R-06 | REVENUE.CHANNEL_TICK (celery beat per channel) | plan → channel-run → judge | channel worker CH1..CH6, OUTPUT_JUDGE |
| R-07 | SYSTEM.SELF_IMPROVE (nightly 03:00 PT) | plan → read-ops → propose → judge → human-PR | IMPROVEMENT worker, human |

## 2. Envelope schema (one per event)
See `icm/context/ENVELOPES.md` for full JSON schemas. Every envelope has:
- `event_id` (uuid v4, `evt_` prefix)
- `route` (R-NN name)
- `stage` (the step this envelope represents)
- `ts` (ISO 8601 UTC)
- `services_touched` (list, ≤3 per L2)
- `blast_radius_usd` (float, ≤ human threshold per L3)
- `worker_profile` and `worker_model` actually used
- `judge_verdict` if judged
- `next_action` (next route-stage)

## 3. Failure modes
- Worker timeout (10 min hard cap per item) → `judge_verdict="halt"`, re-queue with lower-cost profile
- Judge `halt` → ops/`<date>/halt-<event_id>.json` + human notification via Telegram
- Circuit breaker: 3 halts in 1h on same route → pause that route, page human

## 4. Replay
Any envelope in `icm/memory/ops/<date>/` can be replayed via `python -m backend.cli replay <event_id>` — re-runs the route from that stage with the same envelope header.