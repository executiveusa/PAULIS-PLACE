# TARS + Trail Mix + Fleet Observability — Execution Plan

## Goal
Make the five-agent architecture operational, with TARS as the public-facing 3D operator and Trail Mix as TARS's music/radio domain, while PAULIS-PLACE remains the canonical mission/evidence control plane and the observer surfaces show truthful runtime state.

## Hardcore definition of done
Done does **not** mean a page renders, a deployment is READY, or an agent says it worked.

Done means all of the following are proven with live evidence:

1. PR #14 architecture is merged to `main`.
2. TARS has a production landing/front door that uses a TARS-specific interactive 3D body, not a generic stock robot.
3. On desktop, TARS reacts to pointer movement; on mobile, touch targets on his body are large enough to use and invoke real bounded actions.
4. Each visible TARS hotspot is mapped to a real backend capability or a truthful unavailable state; no fake/demo success data.
5. TARS can create/read Trail Mix work through an adapter contract without making AzuraCast/Trail Mix itself the agent brain.
6. Trail Mix has its own landing/product surface connected to the same bounded TARS music/radio actions.
7. One real end-to-end music/radio mission produces durable mission/task/runtime/tool/checkpoint/evidence records in the canonical PAULIS-PLACE data model.
8. Hermes can delegate a bounded Trail Mix mission to TARS and receive a verified result.
9. Lightning/watchdog can observe liveness, progress, cost, errors and repeated failures without killing healthy long-running jobs by wall-clock age alone.
10. Pi private context remains separated from company/public observation.
11. Jarvis/voice routes a high-level instruction to the correct agent without the human needing a terminal.
12. The fleet dashboard and 3D/public observer consume a sanitized projection of canonical state; they never invent activity.
13. Security blockers are resolved or explicitly block production: no committed secrets, no unsafe public write endpoints, approval gates preserved.
14. Production URLs are live, smoke-tested on desktop and mobile, and rollback commits/deployments are recorded.

## Canonical system boundaries

- **Hermes / Pauli** — business orchestrator; creates/decomposes missions.
- **Pi** — private Human OS.
- **Lightning** — watchdog, critic, memory curator, liveness/evaluation layer.
- **TARS** — bounded operator; computer/media/music execution; Trail Mix character/product.
- **Jarvis** — voice/phone/glasses presence and command ingress.
- **PAULIS-PLACE** — canonical mission/task/approval/runtime/evidence state.
- **Trail Mix** — product/domain system for radio/music. Current source repo is `executiveusa/trail-mixx-source-code`, a fork of AzuraCast (AGPL-3.0).
- **Open-Molt / Pauli World / dashboard** — sanitized observation projections only.

## Seven phases

### Phase 1 — Lock architecture and establish truth baseline
- Confirm PR #14 merged.
- Inspect TARS, Trail Mix, PAULIS-PLACE, current Vercel deployment and canonical Supabase state.
- Record duplicate/legacy identities (TARS vs BARS) and existing runtime authority.
- Define TARS <-> Trail Mix adapter contract before implementation.

**Exit proof:** exact repos/branches/deployments/contracts documented; no unresolved ambiguity about source of truth.

### Phase 2 — TARS 3D front door
- Replace generic/legacy presentation with TARS-specific 3D body.
- Prefer self-contained Three.js/procedural TARS if no owned Spline scene exists; Spline can be used only with an owned TARS scene.
- Cursor/touch-responsive lighting/pose.
- Raycast/touch hotspots on body.
- Mobile-first hit areas, reduced-motion fallback and performance budget.
- Frontend talks to existing TARS backend; it does not duplicate agent logic.

Initial hotspot contract:
- head/visor: TALK / voice
- chest: MISSION / chat
- left arm: TRAIL MIX / radio control
- right arm: BUILD / computer-use mission
- left leg: JOBS / long-running work
- right leg: STATUS / evidence and health
- center/abort zone: STOP / bounded cancellation

**Exit proof:** production preview on desktop and phone; hotspots invoke real endpoints or explicit unavailable states.

### Phase 3 — Trail Mix adapter + landing page
- Treat `trail-mixx-source-code` as the Trail Mix source product and radio engine.
- Do not merge the entire AGPL codebase into TARS.
- Add a narrow `trailmix` adapter/tool contract to TARS for station status, now playing, playlists/queues, scheduling and bounded radio operations supported by the actual Trail Mix/AzuraCast API.
- Build a Trail Mix landing/product surface that introduces TARS as the operator.
- Separate read actions from writes; writes require appropriate mission approval.

**Exit proof:** TARS reads real Trail Mix station state and completes one harmless read-only mission with evidence.

### Phase 4 — Real bounded execution + Golden Path
- Reconcile one canonical runtime/router authority.
- Add dynamic capability/privacy/cost routing.
- Resume the existing Golden Path mission instead of fabricating completion.
- Add a music/radio Golden Path using the same mission/evidence model.

**Exit proof:** non-demo runtime/tool/checkpoint/evidence rows exist and independently verify outcome.

### Phase 5 — Long-running agents + Lightning
- Replace fixed elapsed-time failure logic with heartbeat/checkpoint/progress semantics.
- Lightning consumes missions, runtime runs, tool runs, checkpoints, evidence, costs and incidents.
- Add recovery, retry-with-strategy-change, and escalation rules.

**Exit proof:** a healthy job longer than ten minutes stays healthy; a lost-heartbeat job is detected and recovered/escalated truthfully.

### Phase 6 — One-device/voice control + observability
- Jarvis ingress for voice/phone/glasses.
- Hermes/Pi privacy-aware routing.
- Fleet view shows five permanent agents plus temporary workers.
- Open-Molt/Pauli World receives sanitized canonical events.
- Pauli Deck/mobile becomes the operational control surface rather than a second authority.

**Exit proof:** voice -> routed mission -> execution -> evidence -> observer update works without terminal use.

### Phase 7 — Production gauntlet, security, rollout
- Mobile/desktop interaction QA.
- Security scan and secret remediation.
- Cost/route failure tests.
- Approval/rollback tests.
- Remove or clearly label demo fallbacks from production proof paths.
- Deploy TARS and Trail Mix public surfaces.
- Record production URLs and rollback points.

**Exit proof:** all 14 done conditions pass; independent judge/gauntlet evidence attached; production status is HEALTHY, not merely DEPLOYED.

## Updated TODO order

1. PR #14 merge — complete.
2. Phase 1 audit and adapter contract — active.
3. TARS 3D front door and real hotspot API mapping.
4. Trail Mix adapter and landing page.
5. Canonical runtime/model router repair.
6. Golden Path runtime proof.
7. Long-running heartbeat/checkpoint repair.
8. Lightning watcher/evaluation integration.
9. Jarvis one-device/voice ingress.
10. Fleet/public 3D observation projection.
11. Security, mobile QA, production rollout.

## Non-negotiables

- No fake activity can satisfy proof.
- No agent self-certifies its own completion.
- Public observers are projections, never authorities.
- Private Pi context cannot leak to public/company surfaces by default.
- No destructive Trail Mix action without explicit policy/approval.
- No dependency on a specific music generation vendor in the TARS identity; vendor adapters remain replaceable.
- AGPL obligations for the Trail Mix/AzuraCast fork must be preserved.
