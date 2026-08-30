# ICM Context Contract

## Job

This folder is the stable **factory/reference layer** for boundaries agents must not guess: repo maps, access policy, envelopes, registries, task-profile requirements, event contracts and shared schemas.

## Reads

A task loads only the context explicitly required by its instruction. Context is not a substitute for loading every file.

## Writes

Runtime outcomes do not belong here. A recurring verified pattern may be proposed for promotion, but promotion is a reviewed change.

## Rules

- One authoritative home per contract.
- Model/provider choices stay behind runtime routing; context describes capabilities and constraints.
- Secrets never appear here.
- Client/private facts remain scoped to authorized records, not global context.
- When a referenced boundary file is missing, stop and report the missing contract rather than guessing.

## Human check

Changes to access, identity, envelopes, external-system contracts, financial limits or autonomy boundaries require the applicable owner review before becoming authoritative.