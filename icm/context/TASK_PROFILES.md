# TASK PROFILES — Capability Routing Contract

> Runtime adapter: `backend/services/profile_router.py`
> Authority: this file defines profile intent/capability. Runtime code resolves current providers/models.

## Rule

Instructions and agents request a **profile**, never a specific model. Provider/model availability, price and fallback may change without rewriting ICM policy.

| Profile | Use for | Required behavior |
|---|---|---|
| `plan` | decomposition, dependencies, acceptance contracts | strong reasoning, structured output, cost-aware planning |
| `judge` | independent adversarial review | must be independent from the worker that produced the judged artifact; structured verdict |
| `implement` | bounded code/system changes | tool-capable where required, preserves repo conventions, returns evidence and rollback |
| `write_short` | outreach, concise copy, short operator text | concise, audience-aware, claim-safe |
| `write_long` | reports, proposals, long-form synthesis | long-context coherence, source separation, structured sections |
| `score` | ranking, qualification, rubric evaluation | deterministic/structured scoring with evidence refs |
| `test` | verification, failure-path checks, acceptance testing | skeptical validation, reproducible evidence |
| `docs` | documentation and contract maintenance | precise paths, no invented runtime claims |

## Routing invariants

1. The caller declares the minimum capability needed: tool use, JSON/structured output, vision, context length, privacy boundary, latency/cost ceiling.
2. A fallback that loses a required capability is a failure, not a successful downgrade.
3. Judge work must not resolve to the same concrete model that produced the work being judged when independent review is required.
4. Secrets and private context follow `CONTEXT_ACCESS_POLICY.md` regardless of provider.
5. Runtime receipts record the resolved profile/provider/model so later audits can reproduce what actually happened.
6. ICM instructions remain model-agnostic even when runtime code contains current implementation mappings.

## Proof-first defaults

- SCAN/QUALIFY: `plan` and/or `score`
- MODEL/PROVE: select the smallest existing specialist capability; use `implement`, `write_short`, `write_long`, or another authorized skill as appropriate
- JUDGE: `judge` plus independent specialist review when needed
- VERIFY: `test`/`score`
- COMPOUND: `docs` with reviewed promotion into memory/patterns

The profile names are stable contracts; concrete routing is replaceable runtime configuration.