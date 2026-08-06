# ENVELOPES — JSON Schemas for the Yappyverse Event Bus

> File: `icm/context/ENVELOPES.md`

All envelopes share a header. Body varies by route+stage.

## 0. Header (every envelope)
```json
{
  "event_id": "evt_<uuid4>",
  "route": "R-0N.NAME",
  "stage": "<SCAN|SCORE|COUNCIL|DESIGN|PUBLISH|RECONCILE|LEDGER|CELEBRATE|TICK|SELF_IMPROVE|...>",
  "ts": "<ISO8601 UTC>",
  "services_touched": ["<list>"],
  "blast_radius_usd": <float>,
  "worker_profile": "scan|score|judge|implement|write_short|write_long|...",
  "worker_model": "<model id used>",
  "judge_verdict": "accept|reject|halt|null",
  "judge_model": "<model id used or null>",
  "envelope_version": "1.0",
  "next_action": "<next route-stage string or null>"
}
```

## 1. R-01 scan_body
```json
{"trend_id":"trd_<slug>","keyword":"<text>","source":"<...>","velocity":<0-1>,"first_seen":"<ISO>","samples":["..."]}
```

## 2. R-01 score_body
```json
{"trend_id":"trd_<slug>","scores":{"velocity":0-20,"durability":0-20,"margin":0-20,"channel_fit":0-20,"bridge_risk":0-20},"total":0-100,"recommended_channel":"CH1..CH6"}
```

## 3. R-03 council_body
```json
{"debate_id":"deb_<uuid>","proposal":"...","advocate_arg":"...","critic_arg":"...","ruling":"APPROVE|REJECT|MODIFY","modifications":null,"judge_reasoning":"...","expires_at":"<ISO>"}
```

## 4. R-02 design_body
```json
{"product_id":"prd_<uuid>","channel":"CH1..CH6","artifact_type":"...","artifact_path":"..."}
```

## 5. R-02 publish_body
```json
{"product_id":"prd_<uuid>","platforms_attempted":[...],"platforms_succeeded":[...],"platforms_failed":[{"platform":"...","reason":"..."}],"post_urls":{...},"lounge_scene_id":"scn_<uuid>"}
```

## 6. R-05 reconcile_body
```json
{"payment_id":"pay_<uuid>","provider":"creem|btcpay|stripe","amount_usd":<float>,"customer_ref":"...","product_id":"prd_<uuid>","granted_access":[...],"ledger_entry_id":"led_<uuid>"}
```

## 7. R-06 tick_body
```json
{"channel":"CH1..CH6","tick_id":"tik_<uuid>","result_summary":"...","revenue_delta_usd":<float>,"cost_delta_usd":<float>}
```

## 8. R-07 self_improve_body
```json
{"report_id":"rpt_<uuid>","date":"<YYYY-MM-DD>","weak_axes":["..."],"proposed_prs":[{"repo":"...","title":"...","branch":"...","body":"..."}]}
```

## 9. R-04 voice_body
```json
{"command_id":"cmd_<uuid>","raw_transcript":"...","intent":"<who_owns|whats_hot|how_is_money|post_that|whos_paying|tell_about|cut_it|human_moment>","target_avatar":"av_<id>","safety_verdict":"accept|reject|halt","response_text":"..."}
```

## 10. Lounge scene envelope
```json
{"scene_id":"scn_<uuid>","trigger_event_id":"evt_<...>","avatars":[{"id":"av_<id>","action":"<walk_to_bar|say|react|smoke_idle|celebrate>","line":"..."}],"duration_sec":<int>}
```

## 11. Halt envelope (covers L1/L2/L3/L4 violations)
```json
{"halt_id":"hlt_<uuid>","source_event_id":"evt_<...>","law_violated":"L1|L2|L3|L4","severity":"warn|hard","reasoning":"...","suggested_fix":"..."}
```
Halt envelopes go to `icm/memory/ops/<date>/halt-<uuid>.json` and notify the human via Telegram.