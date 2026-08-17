# Skill: Pricing Market Gate (Pauli's Place Adapter)

## Role

Pauli's Place is a product factory, not the pricing authority. For every `SELL` product, this skill must run before public pricing is published or production billing is activated.

## Authority

Canonical pricing authority: **Terabithia Pricing Intelligence**.

Pauli's Place may:
- define ICP and outcome
- propose packages and candidate prices
- collect Van Westendorp responses
- estimate COGS and customer value
- run paid pilots and price experiments
- submit evidence to Terabithia

Pauli's Place may not:
- mark its own pricing `PRICING_PASS`
- convert missing evidence into synthetic evidence
- publish a market-ready price when Terabithia is unavailable
- silently bypass an expired, conditional, or failed decision

## Required factory sequence

1. Define product + segment.
2. Record COGS and target gross margin.
3. Record Van Westendorp observations from qualified prospects.
4. Record competitive/status-quo alternatives.
5. Record customer-value assumptions separately from observations.
6. Test candidate pricing with real buyers.
7. Call `POST /api/pricing/evaluate`.
8. Continue to public launch only on `PRICING_PASS` with confidence >= 85.

## Fail closed

If Terabithia credentials, endpoint, authoritative decision fields, or methodology version are missing, return:

`BLOCKED — UNVERIFIED PRICING`

The factory may continue research/prototyping but must not claim market-ready pricing.

## Configuration

Runtime secrets/configuration only:
- `TERABITHIA_PRICING_URL`
- `TERABITHIA_API_KEY`

Never commit the API key.

## Gate meanings

- `PRICING_PASS`: public pricing/billing may proceed, subject to the rest of the launch gates.
- `PRICING_CONDITIONAL`: run paid pilot / collect missing evidence.
- `PRICING_FAIL`: reprice, repackage, or revalidate before launch.
