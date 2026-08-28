# Phase 5 — Governed Software Factory

Status: implementation active on `feat/phase-5-software-factory`.
Canonical issue: #33.

Scope:
- structured acceptance spec before code changes
- mission-bound isolated workspace reference
- deterministic `pauli/` branch namespace; autonomous `main`/`master` writes blocked
- capability-gated workspace, GitHub branch writes, and preview deployment
- immutable redacted stage receipts for spec/workspace/branch/build/test/critic/repair/preview/guardian/production
- failed build/test/critic/guardian returns the operation to repair instead of completion
- replay-safe preview deployment identity
- production deployment represented by canonical `pauli.approvals` action `software.production.deploy`
- production deployment is not autonomous in this phase

Proof target:
One bounded mission reaches a verified preview with branch, commit, build, test, critic, Guardian, preview URL, and evidence receipts. Full repo CI must be green before merge to `main`.
