# Phase 6 — Governed Digital Product Factory

Status: implementation active on `feat/phase-6-digital-product-factory`.
Canonical issue: #35.

Existing ICM reuse:
- `DESIGNER.md` remains the artifact-generation contract for ebooks/KDP and other product shapes.
- `PUBLISHER.md` remains downstream broadcast logic after approval.

Phase 6 authority:
- audience/problem/offer brief before generation
- explicit research provenance before artifact completion
- deterministic artifact and package SHA-256 identity
- real file metadata required for sell-ready packages
- objective quality checks plus independent critic and Guardian evidence
- failures route to repair, never synthetic completion
- replay-safe distribution/listing draft identity
- `digital.publish.activate` canonical approval before public sale activation
- no autonomous public publishing

Proof target:
One mission reaches a verified sell-ready package and distribution draft with provenance, artifact hash, package hash, quality/critic/Guardian receipts, and evidence. Full repo CI must be green before merge to `main`.
