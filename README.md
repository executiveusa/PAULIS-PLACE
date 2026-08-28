# Pauli's Place

**Pauli's Place is a bilingual, voice-first autonomous business operating environment.** A human states intent in plain English or Mexican Spanish, talks directly to persistent cartoon AI agents, and observes those agents collaborate inside a live 3D world while the real work happens underneath through missions, tools, computers, models, integrations, evidence, approvals, and measurable outcomes.

## North Star

> Human intent → Pauli mission → autonomous execution → verified outcome.

The human should not have to operate Git, Docker, cloud infrastructure, model routing, MCP servers, schedulers, or deployment tooling. Those remain implementation details behind Pauli and the other agents.

## Core product layers

- **Pauli Voice** — web/mobile voice, phone, and messaging entry points; English first, Mexican Spanish second; mixed-language conversations supported.
- **Mission Control** — durable typed missions, tasks, budgets, approvals, evidence, checkpoints, and outcome state.
- **Agent Runtime** — model-independent agents with persistent identity, heart/soul files, skills, memory, and runtime adapters.
- **AutoModel Router** — chooses the best adequate model by capability, privacy, latency, price, and historical results.
- **Pauli Compute** — logical agent workstations with local, Docker, Hostinger/Coolify, Windows, RunPod, and Orgo-fallback providers.
- **Pauli Integrations Bus** — Composio-backed SaaS connectivity plus native integrations for critical deterministic systems.
- **Factory Kernel** — deterministic sequencing, tests, retries, evidence, Guardian review, and Gauntlet quality loops.
- **Pauli Signal** — experiments, revenue attribution, treasury rules, cost tracking, and SCALE/ITERATE/HOLD/KILL decisions.
- **Pauli's World** — live 3D observability where avatars correspond to real agents and real operational state.
- **Pauli Studio** — programmatic and generative media from verified world/business events.

## Product rules

- Canonical spelling is **Pauli**, **Pauli's Place**, and **Pauli's World**.
- Real companies are strict tenants with isolated memory, credentials, budgets, agents, communications, and records.
- Zero-cost reversible work is autonomous.
- Pauli may approve reversible paid work up to the configured policy ceiling.
- Production site launches, outbound email, new outbound-call campaigns, proposals, irreversible actions, and frontier-model use require human approval.
- External approvals are scoped capabilities, not blanket permission.
- No agent may claim completion without objective evidence required by the mission acceptance contract.
- The 3D world must display real backend state rather than fabricated activity.
- Ordinary work loops until the requested outcome is achieved or a real circuit breaker is reached.

## Composio integration

Composio is the broad SaaS integration fabric, not the Pauli control plane. Pauli retains tenant identity, mission authority, approvals, auditing, and budgets.

Current implementation:

- tenant/actor-scoped Composio entity IDs
- autonomous read-only sessions using read-only tool hints
- explicit toolkit allowlists
- hosted MCP session support for compatible runtimes
- human account-connection flow
- approval-gated action-session contract
- dormant behavior when `COMPOSIO_API_KEY` is absent

See `docs/integrations/COMPOSIO.md`.

## Control-plane database

The canonical Supabase/Postgres schema is versioned at:

`backend/supabase/migrations/20260809_paulis_place_control_plane.sql`

It defines tenant isolation and the shared operational spine for:

- tenants and memberships
- persistent agents
- missions and mission events
- tasks
- scoped approvals
- compute sessions
- evidence
- integration connections
- world locations and agent presence
- experiments
- treasury entries
- office/document references

RLS is enabled on all tenant-owned tables. A user must be a member of a tenant to read or write tenant data. Public world data should be projected through explicit public APIs rather than by weakening tenant policies.

## Current applications

```text
frontend/     Next.js application, dashboards, approvals, research, observation, integrations, 3D lounge/world prototype
backend/      FastAPI API, agents, services, model routing, event bus, workers, payments, research, voice, integrations
icm/          durable context and operating artifacts
beads/        work tracking
printed-clis/ CLI/tooling experiments and adapters
```

## Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend
PYTHONPATH=. pytest -q
```

Composio-focused tests:

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_composio.py
```

## Environment

Copy `.env.example` and provide only the integrations you intend to activate. Missing optional providers should remain dormant rather than crash the system.

Important variables include:

- `DATABASE_URL`
- `REDIS_URL`
- `COMPOSIO_API_KEY`
- model-provider keys
- Twilio/voice credentials when enabled
- Vercel/Coolify/compute provider credentials when enabled
- Printify shop/token when the POD factory is enabled
- Etsy API key/secret, OAuth token, shop ID, shipping profile ID, and readiness-state ID when Etsy POD is enabled

Never commit secrets.

## Governed POD revenue loop

The first commercial execution path is a replay-safe Printify → Etsy physical-POD workflow. The canonical service is `backend/services/pod_workflow.py`, backed by the additive `pauli.commerce_operations` ledger.

Rules for this path:

- Printify blueprint, provider, variants, shop, and uploaded image are verified before product creation.
- Every external write passes through the capability guard; missing/revoked grants fail closed.
- External IDs are persisted after each successful stage so retry/recovery does not silently duplicate products or listings.
- Etsy physical drafts require real shop, shipping-profile, processing/readiness-profile, and taxonomy context.
- Etsy listings remain drafts until a verified image exists and the canonical `pauli.approvals` publish gate is approved.
- Final publish is a distinct consequential capability and is never inferred from a UI button or product status.
- Published state is verified back from the providers before Pauli may report success.
- Missing credentials/configuration are blockers, never synthetic success.

## Governed software factory

Software missions use `backend/services/software_factory.py` and the `pauli.software_operations` / `pauli.software_receipts` ledger.

Rules for this path:

- A structured objective and acceptance criteria are persisted before code work begins.
- Each mission uses an isolated workspace and a deterministic `pauli/` branch; autonomous workers cannot target `main`, `master`, or production refs.
- Workspace use, GitHub branch writes, and preview deployments pass through the same deny-by-default capability guard used by other actuators.
- Build and test receipts must contain objective passing exit status before the operation can advance.
- Independent critic and Guardian receipts must cite real artifact evidence; rejection returns the operation to repair.
- Executor commands are bounded argv lists, not shell strings; shell chaining and redirection are rejected by contract.
- A preview deployment ID and HTTPS URL are persisted so retries reuse the same deployment record instead of inventing duplicate success.
- Production deployment is a distinct `software.production.deploy` action and requires canonical human approval after a verified preview.
- Owner-facing completion should present outcome and evidence first; branch, commit, command, and runtime traces remain drill-down detail.

## Governed digital product factory

Digital-product missions reuse the existing Designer and Publisher ICM roles, with `backend/services/digital_product_factory.py` as the durable package/evidence authority and `pauli.digital_product_operations` / `pauli.digital_product_receipts` as the ledger.

Rules for this path:

- Audience, problem, offer, product type, and acceptance criteria are persisted before generation.
- Research provenance is mandatory; each research claim requires a source and retrieval timestamp before artifact completion.
- Real artifact metadata is recorded and hashed before packaging.
- Sell-ready package manifests require a version, format, title, and at least one non-empty file with SHA-256 identity and byte size.
- Objective quality checks, independent critic evidence, and Guardian evidence must all pass; failures return the operation to repair.
- Listing/delivery drafts are capability-gated and replay-safe through a persisted distribution draft ID.
- Public sale activation is a distinct `digital.publish.activate` action and requires canonical human approval.
- Designer and Publisher do not become alternate approval authorities; the control plane retains mission, evidence, budget, and approval authority.

## Business intelligence and owner brief

The owner outcome layer uses `backend/services/business_intelligence.py` and source-qualified snapshots in `pauli.business_metric_snapshots` / `pauli.owner_briefs`.

Rules for this layer:

- Tenant-scoped money is read from `pauli.economic_events`; the older `yappy_ledger` is not used directly for owner totals because it lacks `organization_id` isolation.
- Missing financial coverage returns unknown revenue/cost/profit values, never fabricated zeros.
- Stale financial coverage is labeled stale and suppresses scaling recommendations until refreshed.
- Profit is computed deterministically as revenue minus costs, fees, and refunds; payouts are tracked separately rather than double-counted as expense.
- POD, software, and digital-product states come from their governed operation ledgers, while approvals and workforce state come from canonical control-plane tables.
- Every persisted snapshot carries provenance, coverage status, an as-of timestamp, and a deterministic source hash.
- Watcher-style recommendations cite the metric keys that justify each decision.
- The owner brief follows **Outcome → Decision → Evidence → Needs You / Working Now**, with technical traces as drill-down detail.

## Deployment direction

- **Vercel** — mobile/web frontend and previews.
- **Hostinger + Coolify** — persistent backend, workers, schedulers, and owned CPU workloads.
- **Supabase/Postgres** — canonical multi-tenant control-plane data.
- **RunPod/Fal** — specialized GPU/media workloads where appropriate.
- **Orgo** — fallback computer provider while Pauli Compute reaches full provider coverage.

## Golden Path #001

The first full-system acceptance mission is:

> “Pauli, find a nonprofit that clearly needs a better conversion website, research it, build a personalized superior prototype, deploy the preview, and call me when it's ready.”

The first run stops before contacting the nonprofit. It must create the mission, research the opportunity, assemble agents, provision compute, build and visually verify a preview, produce evidence, update world state and office records, and notify the human through the configured voice/telephony path.

## Gauntlet rule

For every meaningful output, establish a named comparable reference bar. A builder produces the artifact; an independent fresh-context critic compares the real artifact against the reference, chooses a winner, identifies the single largest gap, and returns the gap for repair. The loop ends only when our output wins, the defined outcome is achieved, or a genuine budget/authority/safety/external circuit breaker applies.

Scores such as “8/10” are not completion evidence.
