# CONTEXT ACCESS POLICY — Queryable Company, Private Human

## Goal

Make the company queryable without making every piece of the owner's life globally readable. Context must be useful, attributable, current, and permission-scoped.

## Canonical namespaces

| Namespace | Examples | Default readers | Public/free routing |
|---|---|---|---|
| `shared` | operating laws, schemas, tool contracts, glossary | all named agents | allowed if no sensitive data |
| `company` | goals, offers, clients, meetings, decisions, GitHub/Supabase/Notion references | Hermes, Lightning; scoped workers | sanitized only |
| `personal` | diary, health notes, relationships, spirituality, private goals, creative notebook | Pi; Jarvis for capture | prohibited by default |
| `public` | approved bios, mission summaries, public proof, public agent lore | all agents/public projection | allowed |
| `receipts` | immutable mission events, approvals, evidence references, model/provider usage | Hermes, Lightning, authorized judges | sanitized only |

TARS receives only the context necessary for the active mission. Jarvis receives only the context necessary to route or present the current interaction. Temporary workers receive least-privilege context envelopes and expire after the mission.

## Memory record contract

A durable memory item should carry enough metadata to prevent a fluent guess from becoming truth:

```json
{
  "id": "mem_...",
  "namespace": "company|personal|shared|public|receipts",
  "kind": "decision|fact|preference|assumption|goal|lesson|relationship|event",
  "statement": "...",
  "source_ref": "...",
  "source_type": "voice_diary|meeting|email|calendar|github|database|human|agent",
  "recorded_at": "ISO-8601",
  "effective_at": "ISO-8601",
  "authority": "human|system|external_source|inference",
  "confidence": 0.0,
  "sensitivity": "public|internal|private|restricted",
  "supersedes": null,
  "expires_at": null,
  "goal_refs": [],
  "mission_refs": []
}
```

Raw source records are append-only. Derived summaries may change, but the source and supersession chain must remain inspectable.

## Voice diary / uncodified context

Jarvis provides an optional low-friction voice capture. Pi or Hermes can prompt for short reflection when useful:

- What changed today?
- What did you decide, and why?
- What did someone actually need that was different from what they asked for?
- What belief or priority changed?
- What should the agents know tomorrow?
- What should remain private?

The capture is transcribed, classified into `personal` and/or `company`, linked to relevant entities/goals, and stored with provenance. High-impact inferred memories become proposals until approved by the owner. A private entry never becomes company/public context merely because it is relevant.

## Query-before-copy principle

Prefer connectors and stable references over copying entire mailboxes, drives, or databases into one vector store. The context layer should know where truth lives, query it when needed, and cache only derived memory with provenance.

## Authority order

When sources conflict, use this order unless a domain policy overrides it:

1. explicit current human decision;
2. canonical system of record;
3. verified mission evidence / signed receipt;
4. recent direct source such as meeting/email/calendar;
5. approved derived memory;
6. agent inference.

Never silently resolve a conflict. Record the contradiction and escalate when it changes an action.

## Public projection

Open-Molt, Pauli's World, and other public observability surfaces receive an allow-listed projection only. They may show approved mission state, agent status, public evidence, and impact summaries. They must never receive credentials, private diary content, private health/personal context, raw client data, hidden prompts, or unredacted internal tool payloads.