# AgentForge Assimilation into Pauli's Place

Source reviewed: `executiveusa/pauli-Agent-Forge`.

Pauli's Place absorbs the production patterns AgentForge already solved, while keeping Pauli Mission Control authoritative. AgentForge remains an optional runtime provider behind a process boundary rather than becoming a second control plane.

## What we take

| AgentForge concept | Pauli's Place destination |
|---|---|
| Agents configured independently from models | `pauli.agents` + AutoModel/runtime policies |
| Personas with static + retrieval sections | agent `identity`, `heart`, `soul`, `persona_static`, `persona_retrieval` |
| Declarative Cogs | `pauli.workflow_definitions` |
| Cog transitions / branching | workflow definition state graph + Mission task dependencies |
| `max_visits` loop protection | task retry/strategy-change policy + Gauntlet/Guardian stop conditions |
| Cog memory nodes | namespaced `pauli.memory_entries` |
| PersonaMemory | agent-scoped persona namespace |
| ChatHistoryMemory | agent/mission chat-history namespace |
| ScratchPad | mission/task scratchpad namespace |
| Model-independent agents | Pauli Agent != Model doctrine |
| API retry/backoff | runtime-provider retry policy and failure classification |
| Sync + async execution | provider adapter contract |

## What remains Pauli-owned

AgentForge does **not** decide:

- tenant authority;
- mission budgets;
- consequential approvals;
- external-send/call/deploy authority;
- canonical agent identity;
- evidence acceptance;
- Guardian policy;
- Gauntlet pass/fail;
- Pauli Compute selection;
- business outcome completion;
- Pauli's World truth state.

Those are control-plane responsibilities.

## Runtime boundary

`backend/services/agentforge_runtime.py` launches AgentForge as an external Python runtime. This gives Pauli access to Cogs/personas/memory without importing AgentForge as the architecture of the whole product.

Provider status is observable:

- `disabled`
- `needs_install`
- `installed_needs_project`
- `ready`

A missing AgentForge installation is dormant/degraded state, not a reason for the entire Pauli API to crash.

## Mission mapping

A mission can select an AgentForge Cog when the workflow is a good fit:

```text
Human intent
  -> Pauli Mission
  -> plan + authority + budget
  -> choose runtime
  -> AgentForge Cog (optional)
  -> outputs/events
  -> independent evidence verification
  -> Guardian/Gauntlet
  -> outcome
```

The mission remains durable even if the runtime is changed to Hermes, Pi, OpenHands, Open Interpreter, Codex or another provider mid-run.

## Memory rule

Memory is never blindly injected into prompts. Every durable memory record carries:

- namespace;
- memory type;
- provenance/source type;
- redacted content;
- `safe_for_prompt`;
- approval state;
- confidence;
- optional expiration.

This adapts AgentForge's useful memory specialization while adding the stricter production safety patterns already proven elsewhere in the Pauli ecosystem.
