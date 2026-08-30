---
name: proof-first-revenue-loop
description: Route an active SELL/revenue mission into the canonical proof-first commercial ICM workflow.
---

# Proof-First Revenue Loop — ICM Skill Adapter

This file is a **thin callable adapter**, not a second source of truth.

## Load

1. `../../instructions/HERMES.md`
2. `../../instructions/PROOF_FIRST_REVENUE_LOOP.md`
3. `../../context/TASK_PROFILES.md` when delegation/judging is required
4. only the active mission/opportunity/evidence required by the current state

## Execute

Follow the canonical state machine:

`SCAN -> QUALIFY -> MODEL -> PROVE -> JUDGE -> APPROVE -> TEST -> VERIFY -> CLOSE -> SCALE -> COMPOUND`

Do not skip receipts or human gates. Do not create a fourth workstream. Do not add software when the current bottleneck is selling, approval, testing or measurement.

## Write

Persist run-specific state/evidence to the existing mission/opportunity/memory product surfaces named by the canonical instruction. Never rewrite ICM factory policy at runtime.

## Done

Return the completion contract defined in `../../instructions/PROOF_FIRST_REVENUE_LOOP.md` with evidence and the exact next human decision, if any.