# ICM — PAULIS-PLACE Control Plane

## Purpose

`icm/` is the model-agnostic operating layer for PAULIS-PLACE. The codebase remains the runtime; ICM tells agents what to load, what contract applies, where state is written, and where a human gate exists.

## Portable spine

- `instructions/` — **WHAT to do.** Stable laws, role contracts, workflows, escalation and approval behavior.
- `context/` — **WHERE/HOW boundaries work.** Repo maps, schemas, envelopes, routing capabilities, registries and access policy.
- `memory/` — **WHAT happened.** Write-once operational evidence, decisions and promoted patterns.

These three folders are the cross-repo portable spine. Existing PAULIS-PLACE extensions have one job each:

- `missions/` — active mission product state.
- `opportunities/` — persistent commercial opportunity records.
- `skills/` — thin callable adapters into canonical instructions/context.
- `handoff/` — human/agent transfer artifacts.

## Load protocol

1. Read this file.
2. Read the relevant folder `CONTEXT.md`.
3. Load only the instruction for the current task.
4. Load only context files named by that instruction.
5. Load relevant prior memory only when the task requires history.
6. Write new run evidence to product/memory surfaces; never rewrite stable factory files at runtime.

For Hermes revenue work, load:

1. `instructions/HERMES.md`
2. `instructions/PROOF_FIRST_REVENUE_LOOP.md`
3. `context/TASK_PROFILES.md` when workers/judges are routed
4. the relevant opportunity/mission record
5. only the evidence required for the current state

## Factory vs product

**Factory:** `instructions/`, `context/`, skill adapters, stable templates/contracts.

**Product:** missions, opportunities, approval packets, proof assets, measurements, receipts and `memory/` run history.

A product result must not be promoted into factory policy merely because it happened once. Recurring verified patterns may be proposed for promotion.

## Human gate

L0/L1 work may run automatically inside policy. L2 requires an explicit standing policy. L3/L4 actions remain human-gated unless a narrower approved policy says otherwise. Sending, publishing, spending, production deployment, destructive changes and commitments are never inferred from a draft.

## Walk test

A cold agent passes when it can answer within this file plus at most two reads:

- What role owns this task?
- Which instruction applies?
- What context is required?
- Where will the result be written?
- What proves completion?
- Does a human need to approve the next transition?

If the answer requires loading the whole repository, the ICM structure is wrong.