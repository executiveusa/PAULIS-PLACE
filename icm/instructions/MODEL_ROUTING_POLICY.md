# MODEL ROUTING POLICY — Cheapest Sufficient, Never Cheapest Blindly

## Goal

Use free and inexpensive inference aggressively where it is safe, but never let a stale price assumption, random free model, or privacy mismatch silently change mission quality or confidentiality.

Hermes declares capability/risk requirements. The router resolves a provider/model at runtime.

## Route classes

| Route | Intended use | Data allowed |
|---|---|---|
| `public_free` | public research fan-out, classification, brainstorming, smoke tests, low-stakes extraction | public/sanitized only |
| `cheap_tool` | repeatable tool use, structured transforms, bounded workers | internal data only when provider policy passes |
| `reasoning` | architecture, planning, difficult synthesis, consequential recommendation | minimum necessary scoped context |
| `builder` | code/artifact generation | repo/task context only |
| `judge` | independent review/gauntlet | artifact + acceptance contract, preferably different provider/model family |
| `sensitive_private` | personal/private/client-sensitive reasoning | provider/model endpoint that satisfies explicit privacy policy; random free routing prohibited |
| `human` | L3/L4 approvals and decisions AI must not own | summarized decision packet |

## Runtime selection contract

Do not hardcode `cost = 0` or assume a model stays free. At dispatch time resolve and record:

- requested route/capabilities;
- selected model and provider;
- tool/JSON/vision/context requirements;
- data-policy status;
- quoted/observed cost when available;
- latency and rate-limit class;
- fallback chain;
- actual model/provider returned by a router;
- token usage and actual charged cost when reported.

Provider and model identifiers are configuration/data, not persona logic.

## Free routing

A free-model router is appropriate only when all of these are true:

1. the task is low consequence;
2. the prompt is public or sanitized;
3. required features can be filtered/verified;
4. nondeterministic model selection will not break acceptance criteria;
5. rate/availability failure has a truthful fallback or stop condition.

If a random free router chooses the actual model, record the returned model in the mission receipt.

Free models may be used as parallel scouts or critics for public information, but a majority vote of cheap models is not proof.

## Privacy gate

Before any external model call, classify context sensitivity. `personal`, credentials, raw client/private data, high-stakes health/legal/financial material, and restricted records cannot be sent to a random free endpoint.

For sensitive routes require an approved provider/endpoint policy such as zero-data-retention or an owner-approved local/private model. If policy metadata is unavailable, fail closed or redact/downscope the prompt.

## Judge independence

For meaningful judged artifacts, prefer a judge from a different model family/provider than the builder. A judge receives the acceptance contract and artifact but not the builder's self-evaluation. The judge cannot deploy, merge, publish, or approve its own policy changes.

## Capability degradation

Fallbacks must preserve required semantics. If the preferred route supports tools/structured output/vision/long context and the fallback does not, the router must return `CAPABILITY_UNAVAILABLE` rather than pretending the task succeeded.

## Budget behavior

Budget exhaustion pauses or reroutes future work; it does not falsify already-incurred cost or silently downgrade a high-risk task to an unsuitable model. Cost caps are mission/policy inputs, not constants embedded in the agent identity.

## Observability

Each model call should be attributable to `mission_id`, `task_id`, `agent_id`, route class, provider, model, privacy classification, start/end time, tokens, cost, result status, and evidence/trace reference. Lightning uses this stream to identify waste, drift, weak fallbacks, and opportunities to promote/demote routes.