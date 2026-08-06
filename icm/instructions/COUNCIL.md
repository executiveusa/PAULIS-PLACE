# COUNCIL — Adversarial Three-Turn Debate

> File: `icm/instructions/COUNCIL.md`
> Route: R-03 · COUNCIL.DEBATE_REQUEST
> Owner: SSSF ADW `backend/agents/council_agent.py`

## 0. Purpose
Every meaningful agent decision must survive a 3-turn adversarial debate before it becomes a locked ruling. No exceptions (L1).

## 1. Roles
- **Advocate** — argues FOR the proposal. Worker profile `write_short` (grok-4.5 / glm-5.2 fast). One sentence thesis + 3 supporting points.
- **Critic** — argues AGAINST. Worker profile `score` (qwen-3.5 / llama-70b). One sentence antithesis + 3 risks.
- **Judge** — locks the ruling. Worker profile `judge` (claude-fable-5 / glm-4.6 high-thinking). Must NOT be the same model as Advocate or Critic.

## 2. The three turns
```
Turn 1 — Advocate speaks (sees only the proposal)
Turn 2 — Critic speaks (sees proposal + Advocate output)
Turn 3 — Judge rules (sees proposal + Advocate + Critic)
```
No rebuttals beyond turn 2. The judge's verdict is final.

## 3. Locked-ruling contract
The judge emits:
```json
{
  "debate_id": "deb_<uuid>",
  "proposal": "<original proposal text>",
  "advocate_arg": "<turn 1>",
  "critic_arg": "<turn 2>",
  "ruling": "APPROVE" | "REJECT" | "MODIFY",
  "modifications": "<if MODIFY, the new proposal text>",
  "judge_model": "<model id>",
  "judge_reasoning": "<one paragraph>",
  "expires_at": "<ISO deadline for re-debate if challenged>"
}
```
Saved to `icm/memory/decisions/<YYYY-MM-DD>/<debate_id>.json`.

## 4. Trigger events
- R-01 REVENUE.NEW_TREND (after Scorer scores > threshold)
- R-03 COUNCIL.DEBATE_REQUEST (any agent proposes a decision with blast_radius > $5 or services_touched >= 2)
- R-06 REVENUE.CHANNEL_TICK (before any channel run that mutates external state)

## 5. Hard limits
- Max 3 turns. No infinite debate.
- If the judge returns `halt`, escalate to human (no auto-proceed).
- Debate cost counts toward L3 cap. Pre-flight declares expected cost.