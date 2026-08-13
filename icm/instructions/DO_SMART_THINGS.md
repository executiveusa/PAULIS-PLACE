# DO SMART THINGS — Proactive Mission Loop

## Purpose

This is not permission to do random work. It is permission to discover and execute the highest-value safe work inside current goals and autonomy boundaries without waiting for the owner to invent every task.

Hermes owns the business loop. Pi may run a separate private personal loop. Lightning observes both within its access policy but never becomes the mission owner.

## Triggers

The loop may run from:

- explicit human command: `do smart things`;
- a scheduled review;
- a relevant system event;
- mission completion/failure;
- a meaningful context/goal change;
- a Lightning observation that warrants reconsideration.

Do not wake the human merely because the loop ran.

## Step 0 — Load only necessary context

Read current goals, the three active workstreams, current missions, unresolved approvals, recent evidence/events, relevant diary/context changes, budgets, and hard blocks. Do not load every skill or every private record.

## Step 1 — Generate candidate actions

Find work the owner did not have to specify. Candidate work should remove a bottleneck, advance an active goal, produce revenue/savings/retention/validated learning, prevent a credible failure, or reduce future human management.

Each candidate must state:

- expected outcome;
- goal/workstream it serves;
- why now;
- evidence that triggered it;
- reversibility;
- estimated human attention required;
- tools/context required;
- confidence;
- stop condition.

## Step 2 — Kill low-value motion

Discard a candidate if it:

- belongs to a fourth active workstream;
- is architecture theater with no user, customer, system outcome, or validated learning;
- duplicates an existing tool, repo, agent, or skill;
- adds software where a skill, adapter, or existing capability is sufficient;
- has no proof condition;
- consumes more human attention than the expected value justifies.

## Step 3 — Risk tier

| Tier | Typical action | Default |
|---|---|---|
| `L0` | read, search, classify, summarize, observe | auto |
| `L1` | reversible internal draft, test, temporary worker, local analysis | auto + receipt |
| `L2` | bounded reversible external action under explicit standing policy | auto only if policy exists |
| `L3` | send/publish, production deploy, DB/schema migration, meaningful spend, external commitment | human approval |
| `L4` | destructive action, secrets/admin, legal decision, high-stakes financial action, medical decision, identity/permissions | hard gate / qualified human |

Expanding the breadth of work never expands the risk tier. Autonomy may grow only inside an already-approved tier.

## Step 4 — Staff the mission

Create one PAULIS-PLACE mission and acceptance contract. Reuse existing skills/personas first. Spawn temporary sidekicks/civilians only when parallelism or specialization creates real advantage. Workers receive least-privilege tools/context and an expiry.

Do not create a permanent agent or repo as a staffing shortcut.

## Step 5 — Execute with heartbeat, not babysitting

Long-running work is allowed. Every long-running worker must emit heartbeat/checkpoint events, current hypothesis/progress, cost, next checkpoint, and recoverable state. Duration alone is not failure.

Circuit breakers use lack of heartbeat, repeated failed attempts, cost/risk limits, dependency failure, or explicit deadline—not a universal short wall-clock timeout.

## Step 6 — Prove the result

Before accepting completion:

1. trace the promised outcome through the actual runtime/canonical state;
2. test the important failure path;
3. collect evidence/receipts;
4. run an independent judge/critic when the artifact is judgeable;
5. compare against a named, fetchable, comparable bar when one exists;
6. reject demo/mock/fallback behavior as proof of a real capability.

A builder cannot approve itself.

## Step 7 — Learn without rewriting history

Lightning reviews new actions/outcomes for drift, recurring failures, duplicated effort, access problems, model/provider weakness, and opportunities to improve prompts/skills/context. Lightning produces proposals. Authoritative facts/goals and consequential policy changes require the appropriate owner or approval gate.

## Step 8 — Protect human attention

Nonurgent progress is batched. The owner should receive an interruption only when:

- an L3/L4 decision is required;
- a time-critical opportunity would expire;
- a high-confidence failure threatens a current goal;
- the system is blocked and cannot safely route around it.

All other information waits for the next briefing.

## Completion report

Every mission closes with:

`OUTCOME | EVIDENCE | COST | WHAT CHANGED | RISKS | ROLLBACK | NEXT | HUMAN DECISION (if any)`

If there is no human decision, say so and stop. Do not manufacture another task merely to keep the system busy.