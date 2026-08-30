# ICM Memory Contract

## Job

This folder is the history/product evidence layer: operational receipts, decisions and promoted patterns that let later runs learn without rewriting what previously happened.

## Write contract

- Prefer append/new-file semantics for run evidence.
- `ops/` holds dated mission/run receipts and judge evidence.
- `decisions/` holds durable human/Council decisions.
- `patterns/` holds recurring verified wins/losses promoted from multiple observations.
- Do not store secrets or unrestricted client-private material here.

## Read contract

Load prior memory only when the current instruction requires history. Do not context-stuff all memory into every run.

## Promotion rule

One outcome is evidence, not a universal rule. A pattern becomes factory guidance only after repeated independent evidence and the appropriate review.

## Human check

Consequential decisions, policy changes and client-sensitive promotions require the applicable owner/approval gate.