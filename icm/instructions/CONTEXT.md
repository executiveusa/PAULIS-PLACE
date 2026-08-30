# ICM Instructions Contract

## Job

This folder stores stable executable policy: role identity, operating laws, workflow order, escalation rules and human-gate behavior.

## Reads

Instructions may point to stable facts/contracts in `../context/` and to explicit run inputs in missions/opportunities/memory. They must not require the whole repo by default.

## Writes

Runtime agents do **not** rewrite instruction files. Changes to this folder are reviewed policy changes.

## Rules

- Keep instructions model-agnostic; declare task profiles/capabilities, not cherished model names.
- Put API/schema/location facts in `../context/`, not here.
- Put run results and history in product/memory surfaces, not here.
- State inputs, ordered process, validation, failure/stop conditions, outputs and human gate.
- Link to one authoritative home for each fact instead of copying it.

## Human check

Any change that expands autonomy, spend authority, publication rights, destructive capability, identity/permission scope or production authority requires explicit human approval.