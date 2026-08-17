# PAULI REPO CONSOLIDATION MAP

> Purpose: reduce repo/agent sprawl without losing useful capabilities.
> Decisions here are architecture triage. Core runtime repos below were inspected. Long-tail forks are classified from current repo metadata/upstream purpose and still require code recon before deletion or archival.

## Decision vocabulary

- **SELL** — bounded product/offer with a realistic near-term customer/revenue path.
- **USE** — active shared platform/runtime/infrastructure component.
- **MERGE** — extract capability into a canonical agent/platform/skill, then retire the duplicate authority after parity proof.
- **PARK** — reference/pattern/possible future capability; no active engineering work.
- **ARCHIVE** — retire only after recon proves no unique capability/production dependency remains.

No deletion is authorized by this document.

## Canonical runtime spine

| Repository | Decision | Destination / rule |
|---|---|---|
| `pauli-hermes-agent` | USE | Canonical business orchestrator. Hermes = Pauli for business. |
| `PAULIS-PLACE` | USE | Canonical mission/execution/evidence/approval platform and ICM home. |
| `pauli-pi-agent` | USE | Migrate permanent identity to private Human OS; preserve engineering capabilities by extracting them into Hermes personas/workers. |
| `pauli-tars-demo-` | SELL | Bounded Trail Mix/music/operator experiment and public character. |
| `pauli-jarvis-demo` | MERGE | Presence/voice/phone/glasses adapter. Remove competing brain/memory authority after parity. |
| `-lightning-claude-memory-agent` | MERGE | Keep Microsoft Agent Lightning as optional optimizer/trainer behind the Lightning watchdog; not a second orchestrator. |
| `pauli-studio-control-plane` | MERGE | Extract fleet/observation adapter and security-harden; PAULIS-PLACE becomes canonical state. Retire duplicate authority after proof. |
| `open-molt-social-purpose` | USE | Public observable-agents/social-proof projection only; never canonical private state. |
| `pauli-deck` | MERGE | Thin mobile control/approval view over PAULIS-PLACE; no separate truth. |
| `pauli-mobile-agent` | MERGE | Jarvis mobile/device adapter. |

## Orchestration and agent-harness forks

These do not become permanent brains. Extract proven primitives only when they beat Hermes/PAULIS-PLACE on a measurable need.

| Repository | Decision | Destination / rule |
|---|---|---|
| `pauli-prime-agent` | PARK | Candidate long-running specialist worker patterns. |
| `paperclip-pauli-clip` | PARK | Registry/orchestration patterns; do not create a competing company authority. |
| `pauli-Agent-Forge` | PARK | Framework patterns only. |
| `Paulis-jcode` | PARK | Coding harness patterns; use only as a bounded worker if proven better. |
| `pauli-oh-my-codex` | PARK | Subagent/HUD patterns. |
| `pauli-claw-code` | PARK | Harness patterns. |
| `pauli-agency-agents` | MERGE | Persona/process library into ICM personas/skills, not permanent agents. |
| `paulis-awesome-codex-subagents` | MERGE | Specialist persona catalog; install on demand, do not preload. |
| `paulis-agenthub` | PARK | Agent-hub patterns; PAULIS-PLACE remains mission authority. |
| `pauli-agent-orchestrator` | PARK | Parallel coding patterns only; Hermes already orchestrates. |
| `pauli-goose-coding-agent-` | PARK | Optional coding worker/harness. |
| `pauli-nullclaw` | PARK | Lightweight assistant infrastructure reference. |
| `paulis-deep-agent` | PARK | Deep-reasoning/toolset patterns, callable as a specialist if later justified. |
| `Pauli-claw-work` | PARK | Revenue-work experiment patterns; require PBN evidence before activation. |
| `open-agent-platform-pauli` | PARK | UI/platform reference; not another source of truth. |
| `pauli-open-cowork` | MERGE | Desktop/sandbox patterns into Jarvis/Hermes presence/execution adapters. |
| `pauli-skales` | MERGE | Desktop-agent/Telegram/provider ideas into Jarvis; avoid another permanent desktop brain. |
| `pauli-nicks-stack-orgo` | MERGE | Extract useful Hermes onboarding/Telegram/Composio/Obsidian integration patterns. |

## Memory, context, ontology, learning

Use one context fabric with namespaces/provenance. These repos are component/pattern sources, not independent memories.

| Repository | Decision | Destination / rule |
|---|---|---|
| `pauli-context-ontology-accelerator` | PARK | Borrow ontology/namespace/authorization patterns. Do not adopt heavyweight infrastructure until simple canonical context proves insufficient. |
| `pauli-memory` | MERGE | Memory algorithms/benchmark patterns behind shared context store. |
| `pauli-beads` | MERGE | Work/memory continuity patterns, not a second mission ledger. |
| `pauli-OpenChronicle` | MERGE | Chronicle/event-memory patterns into receipts/derived memory. |
| `pauli-graphify` | MERGE | Text-to-graph utility for approved context ingestion. |
| `pauli-infranodus` | MERGE | Graph analysis/reasoning tool callable from Pi/Hermes. |
| `pauli-my-Brain-Is-Full-Crew` | MERGE | Personal second-brain ideas into Pi after privacy review. |
| `pauli-openhuman` | MERGE | Personal AI patterns into Pi; do not create a competing personal brain. |

## Computer use, web access, communications, integrations

| Repository | Decision | Destination / rule |
|---|---|---|
| `pauli-agent-S-computer-use-` | USE | TARS computer-use specialist tool under mission/approval envelopes. |
| `pauli-agentql` | MERGE | Web interaction/extraction tool for Hermes/TARS. |
| `pauli-brightdata-mcp` | MERGE | Public-web research adapter; use only with current account/policy. |
| `wacli` | MERGE | WhatsApp transport for Jarvis/Hermes. |
| `pauli__mail` | PARK | Agent-to-agent mail pattern only if PAULIS-PLACE event bus cannot cover a proven need. |
| `PAULI-buzz-agent-` | PARK | Communication/hive pattern; avoid competing internal bus. |
| `pauli-antigravity_phone_chat` | MERGE | Remote phone interaction pattern into Jarvis. |
| `pauli-remote-screen-` | MERGE | TARS remote/computer-control adapter when explicitly authorized. |
| `pauli-mcp-ext-apps` | USE | MCP UI protocol/reference for tools needing embedded human UI. |
| `pauli-glot` | PARK | Recon required; likely language/translation capability if code confirms. |

## Skills, coding quality, governance, token efficiency

| Repository | Decision | Destination / rule |
|---|---|---|
| `pauli-agent-skills` | MERGE | Canonical skill library content; deduplicate against other managers. |
| `paulis-skill-kit` | PARK | Skill portability/install patterns. |
| `pauli-skills-` | PARK | Skill-manager patterns; choose one registry mechanism. |
| `pauli-token-saver-jcodemunch-mcp` | USE | Shared token-efficient code recon tool. |
| `pauli-stack-ceo` | MERGE | CEO/engineering/release personas into Hermes ICM personas. |
| `pauli-plans` | MERGE | Human plan/diff review interface; useful approval UI. |
| `pauli-humanizer` | MERGE | Writing quality skill. |
| `pauli-impeccable-design-` | MERGE | Shared design skill. |
| `pauli-taste-skill` | MERGE | Shared design critic/taste skill. |
| `pauli-Uncodixfy` | MERGE | Shared anti-generic-UI design skill. |
| `pauli-design-resources-for-developers` | PARK | Design reference library. |
| `pauli-system-prompts-` | PARK | Research/reference only; never a production authority or secret source. |
| `Pauli-spec-kit` | USE | Specification discipline for agentic builds. |

## Research, intelligence, watchdog and observability

| Repository | Decision | Destination / rule |
|---|---|---|
| `pauli-world-monitor` | MERGE | Hermes/Lightning intelligence tool and situational-awareness view. |
| `pauli-deep-research` | MERGE | Hermes deep-research skill. |
| `pauli-auto-research` | PARK | Research-automation patterns; activate only for a scoped research experiment. |
| `pauli-vibe_cockpit` | MERGE | Lightning/fleet observability patterns. |
| `pauli-self-hosted-uptime-kuma` | USE | Infrastructure health signal consumed by Lightning; not an agent. |
| `pauli-Pomelli` | PARK | Research/brand experiment until a current use case passes PBN. |

## Media, music, video, voice and 3D

Most become TARS/Hermes tools. A heavy engine may remain its own repo if it has a real runtime/deployment reason; it is still not a permanent fleet brain.

| Repository | Decision | Destination / rule |
|---|---|---|
| `pauli-montage-video-agent` | USE | Video-production engine/toolset callable by TARS/Hermes; separate product work may continue outside this fleet migration. |
| `pauli-hyparframe-video` | MERGE | TARS video rendering adapter/skill. |
| `pauli-story-tool-kit` | MERGE | TARS footage transcription/search/editing tool. |
| `pauli-clip-cannon-video` | PARK | Extract unique video/voice capabilities only after comparison with Montage. |
| `pauli-twick-video-editor` | MERGE | Thin timeline/editor UI capability for video workflows. |
| `pauli-hyperedit` | PARK | Compare against Montage/Twick before retaining. |
| `pauli-Open-Generative-AI` | PARK | Model gateway/reference for generated media; avoid duplicate studio unless proven. |
| `paulis-Open-Sora` | PARK | Heavy video-generation backend option, invoked only when justified. |
| `pauli-blender-mcp` | MERGE | TARS 3D tool adapter. |
| `paulis-voicebox` | MERGE | Voice studio capability for Jarvis/TARS. |
| `nano-banana-generator-pauli-fork` | MERGE | Image-generation adapter/template. |
| `Pauli-universe-video` | PARK | Recon/merge into TARS/media system if unique. |
| `pauli-scroll-world` | MERGE | 3D brand/world presentation skill. |
| `pauli-pixel-agents` | PARK | Visual office inspiration/projection; not canonical agent state. |
| `paulisworld-openclaw-3d` | MERGE | 3D observable-agent world patterns; projection only. |

## Security, deployment, sovereignty and infrastructure

| Repository | Decision | Destination / rule |
|---|---|---|
| `pauli-sercets-vault-` | USE | Candidate self-hosted secret-management infrastructure; no secrets in repo code. |
| `pauli-deploy-system` | MERGE | Hermes operations/deployment skill and evidence workflow. |
| `pauli-security-red-hat-` | MERGE | Human-approved security test specialist; never autonomous against unauthorized targets. |
| `pauli-iron-claw` | PARK | Security/privacy architecture reference. |
| `pauli-project-nomad` | PARK | Offline/resilience reference. |
| `pauli-cloud` | PARK | Recon required before assigning infrastructure authority. |

## Brand, marketing, websites and bounded products

These are not new fleet agents. Keep only if they map to an active commercial path or current client/product.

| Repository | Decision | Destination / rule |
|---|---|---|
| `the-pauli-effect-2026` | USE | Brand/public company surface if it remains the current site. |
| `the-pauli-effect` | PARK | Private historical/current code requires recon before consolidation. |
| `pauli-brand-guidelines` | USE | Shared brand/design source. |
| `pauli-comic-funnel` | PARK | Creative/marketing experiment unless tied to active revenue. |
| `paulis-pipeline-websites-` | MERGE | Portfolio pipeline capability into Hermes portfolio stewardship. |
| `pauli-blog` | PARK | Website/content surface unless part of current distribution plan. |
| `pauli-effect-roi-wizard` | MERGE | Revenue-offer calculator/skill for audit/sales workflows if current code supports it. |
| `Awesome-Black-Friday-Cyber-Monday` | PARK | Seasonal research/commerce skill, not permanent agent. |
| `pauli-readme-with-video` | MERGE | Documentation/video skill. |
| `kupuri-media-website` | PARK | Separate client/business product; outside the three active Pauli fleet workstreams unless explicitly promoted. |

## Legal and specialist domains

| Repository | Decision | Destination / rule |
|---|---|---|
| `paulis-attorney-better-call-paul` | MERGE | Hermes legal-assistant skill with mandatory legal/human gate for consequential advice/actions. |

## Immediate three-workstream lock

The fleet consolidation itself does not authorize more active projects. Recommended active set:

| Slot | Workstream | Repos |
|---|---|---|
| Revenue offer | Vibe Audit -> Rescue -> Sovereign Launch proof | Hermes + selected client/project repos |
| Shared platform | Five-agent ICM + PAULIS-PLACE verified execution | `PAULIS-PLACE`, `pauli-hermes-agent`, Pi/Jarvis/Lightning adapters as migration targets |
| Bounded experiment | TARS / Trail Mix music avatar | `pauli-tars-demo-` + only the media adapters it needs |

Open-Molt/3D observability is a **projection of the shared platform**, not a fourth workstream.

## Retirement rule

A duplicate repo can move from MERGE/PARK to ARCHIVE only after:

`unique capability inventory -> dependency check -> extraction/parity proof -> production/reference search -> backup -> redirect/readme -> human approval`

No repo is deleted by an agent solely because a newer architecture looks cleaner.