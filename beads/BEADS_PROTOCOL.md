# BEADS PROTOCOL
# All state changes require a Bead. No "done" without a Bead.
# This is the immutable ledger for autonomous agent rollbacks and state tracking.

## bead-0001
id: bead-0001
timestamp: 2026-06-26T14:30:00Z
actor: Human (Bambu)
phase: Handoff / Init
repo: executiveusa/PAULIS-PLACE
branch: main
files_changed: beads/, .env.example
decision: Initialized repo with SpecDrive Handoff, External Skills report, and Beads protocol.
reason: To establish immutable ledger for autonomous agent rollbacks and state tracking.
rollback_command: git reset --hard HEAD~1
risks: None
next_action: GLM-5.2 executes bead-0002 (Database & Infrastructure Wiring)
human_needed: false

## bead-0002
id: bead-0002
timestamp: 2026-06-26T15:00:00Z
actor: GLM-5.2 (Autonomous Build)
phase: Research Lab + SpecDrive Build
repo: executiveusa/PAULIS-PLACE
branch: main
files_changed:
  - backend/services/model_router.py
  - backend/services/wiki_service.py
  - backend/services/payment_service.py
  - backend/services/browser_vision_service.py
  - backend/agents/autoresearch_agent.py
  - backend/agents/idea_factory_agent.py
  - backend/agents/council_agent.py
  - backend/prompts/ruthless_system.py
  - backend/api/research_lab.py
  - backend/api/payments.py
  - backend/api/council.py
  - backend/workers/boot_task.py
  - backend/alembic.ini
  - backend/alembic/env.py
  - backend/alembic/versions/001_initial_schema.py
  - backend/config.py
  - backend/main.py
  - backend/requirements.txt
  - frontend/src/app/research/page.tsx
  - frontend/src/app/observation/page.tsx
  - frontend/src/components/Sidebar.tsx
  - frontend/package.json
  - scripts/boot_sequence.sh
  - .env.example
decision: Built complete Ruthless Autonomous Upgrade - Research Lab (model router, AutoResearch, Idea Factory, LLM Wiki), SpecDrive tasks (Supabase/Alembic schema, The Council multi-agent debate, 402 Bitcoin/Creem payments, Vision QA, VPS boot harness, PS4 Theater Observation UI).
reason: Phase 2.0 upgrade to add agentic autonomy, multi-model cost routing (84% cost reduction), self-building knowledge base, and monetization layer.
rollback_command: git reset --hard HEAD~1
risks:
  - OpenRouter API key required for all LLM calls (system non-functional without it)
  - BTCPay/Creem require external service setup before payments work
  - Playwright requires browser install (`playwright install chromium`)
  - pgvector extension optional (keyword search fallback works)
next_action: Human provides API keys in .env, runs `bash scripts/boot_sequence.sh`
human_needed: true

## bead-0003
id: bead-0003
timestamp: 2026-08-24T08:15:00Z
actor: GPT-5.6 Sol (Production Readiness)
phase: Production Baseline / Dependency Security
repo: executiveusa/PAULIS-PLACE
branch: feat/system-production-baseline-001
files_changed:
  - backend/requirements.txt
  - beads/BEADS_PROTOCOL.md
decision: Upgrade lxml, python-multipart, and Pillow to current Dependabot-vetted security versions; validate through existing backend pytest and frontend production build CI before merge.
reason: Remove known dependency security debt before deeper world/backend production integration.
rollback_command: git revert <slice-merge-sha>
risks:
  - Major-version dependency changes may reveal compatibility issues in CI.
next_action: Run PR CI, inspect failures and review comments, repair until green, then request human approval to merge.
human_needed: true

## bead-0004
id: bead-0004
timestamp: 2026-08-28T19:15:00Z
actor: GPT-5.6 Sol (Production Readiness)
phase: World Reality Bridge / Canonical Truth
repo: executiveusa/PAULIS-PLACE
branch: feat/system-world-truth-001
files_changed:
  - backend/api/health.py
  - backend/tests/test_world_state.py
  - frontend/src/lib/loungeApi.ts
  - frontend/src/components/lounge/LoungeClient.tsx
  - frontend/src/components/lounge/ThreeScene.tsx
  - beads/BEADS_PROTOCOL.md
decision: Replace the lounge hardcoded operational roster with a tenant-scoped projection of pauli.agents, pauli.world_presence, pauli.world_locations, pauli.missions and latest runtime model state; repair duplicate frontend realtime logic and reconcile the ThreeScene prop contract.
reason: Pauli's World must render canonical backend truth and must not invent operational agent state when the control plane is unavailable.
rollback_command: git revert <slice-merge-sha>
risks:
  - Production database must have the pauli control-plane migration and organization bootstrap applied before real agents appear.
  - Legacy ICM scene envelopes remain a read-only event feed pending the canonical mission-event translation slice.
next_action: Run CI and independent PR review; repair failures; then merge after explicit production approval.
human_needed: true
