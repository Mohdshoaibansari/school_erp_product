# 0003. Bundled paid tier with per-student pricing

- Status: accepted
- Date: 2026-06-20

## Context

The paid tier needs a pricing model. Options: per-module pricing (school picks modules a la carte), bundled pricing (all modules included, pay per student), or tiered bundles (Starter/Growth/Enterprise). Per-module adds billing complexity and frontend gating complexity. Tiered bundles require maintaining multiple entitlement configurations. Per-student bundled pricing is simplest to build and operate.

## Decision

Paid clients pay a single per-student rate and receive all modules. No per-module selection, no a la carte pricing. Module gating logic simplifies to a binary check: is this client free or paid? If paid, all modules are available. The subscription engine (C-07) only needs to track student count and tier status — not individual module entitlements.

## Consequences

- Positive: Simplest pricing, billing, and entitlement logic
- Positive: Clients get full platform value — no feature upsells within paid tier
- Negative: Clients wanting only one paid module pay the same as those wanting all
- Negative: Future tiered pricing would require restructuring C-07 data model
