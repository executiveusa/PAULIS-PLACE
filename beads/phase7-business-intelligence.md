# Phase 7 — Business Intelligence and Owner Outcome Layer

Status: implementation active on `feat/phase-7-business-intelligence`.
Canonical issue: #37.

Source authority:
- money: tenant-scoped `pauli.economic_events`
- POD work: `pauli.commerce_operations`
- software work: `pauli.software_operations`
- digital-product work: `pauli.digital_product_operations`
- approvals: `pauli.approvals`
- workforce: `pauli.agents`

Important legacy finding:
`yappy_ledger` is append-only but not tenant-scoped. It is not used directly for an owner business projection because that could mix organizations. Legacy money remains partial/missing until reconciled into tenant-scoped economic events.

Rules:
- missing financial data is `unknown`, never synthetic `$0`
- stale financial data is labeled stale and blocks scale recommendations
- profit = revenue - cost - fee - refund; payout is tracked separately
- every owner brief persists source hash, provenance, as-of time, and coverage status
- Watcher-style decisions cite metric keys/evidence
- pending consequential actions surface under Needs You
- outcome/decision/evidence precede technical detail

Proof target:
Given verified source rows, produce a deterministic owner brief covering revenue/cost/profit, product/work state, failures, approvals, and evidence. Full repo CI must be green before merge to `main`.
