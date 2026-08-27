# Phase 4 — Governed POD Revenue Loop

Status: PR/CI gate ready.
Canonical issue: #29. Issue #31 is a duplicate and should not be used as a second authority.

Scope:
- current Printify catalog/provider/variant validation
- current Etsy physical-draft contract with shipping/readiness profiles
- replay-safe commerce operation ledger
- capability-gated Printify/Etsy writes
- canonical publish approval through `pauli.approvals`
- verified image requirement before Etsy publish
- per-provider publish completion persistence for partial-failure recovery
- provider-state verification after publish
- legacy product approval endpoint cannot directly publish POD products
- focused fail-closed/idempotency contract tests
- no secrets committed

Phase completion requires full repository CI green and merge to `main`.
