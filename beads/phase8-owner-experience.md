# Phase 8 — Owner Experience

Status: implementation active on `feat/phase-8-owner-experience`.
Canonical issue: #39.

Primary surfaces:
- Home
- Pauli
- Work
- World

Owner hierarchy:
Outcome → Decision → Evidence → Needs You / Working Now → technical trace.

Rules:
- financial cards are sourced from the Phase 7 owner brief
- missing money is shown as Unknown, never fabricated $0
- stale/partial coverage is labeled in plain language
- Pauli is the primary conversational mission-entry surface
- approvals interrupt only under Needs You
- Working Now reflects real agent state only
- provider/runtime/system details stay behind drill-down
- failure states are explicit and never presented as completion
- World remains optional observability
- mobile bottom navigation is first-class

Visual direction:
Apple clarity + Pixar personality + Linear information discipline. Light owner-facing shell, large type, calm spacing, restrained motion, soft depth, and no technical-dashboard density on the default screen.

Proof target:
Full backend suite and frontend production build pass with the new owner projection and no synthetic financial zeros before merge to `main`.
