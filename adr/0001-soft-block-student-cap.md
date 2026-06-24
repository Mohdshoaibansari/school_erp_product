# 0001. Soft-block student cap enforcement

- Status: accepted
- Date: 2026-06-20

## Context

The free tier limits schools to 100 active students. When this limit is reached, the system must respond. Two approaches were considered: hard block (disable functionality, degrade experience) and soft block (continue existing operations, prevent new student creation). Schools rely on the platform for daily operations — an aggressive block would harm trust and create emergencies.

## Decision

Enforce a soft block at 101 students: existing students continue to function, all free modules remain fully operational, attendance and fees work normally. Only the ability to add new students is blocked — the "Add Student" button is disabled, POST /students returns 402, and bulk imports skip over-cap students. No data is deleted, no features are degraded.

## Consequences

- Positive: Schools can continue using the platform without disruption while evaluating upgrade
- Positive: No data loss, no operational emergencies
- Neutral: Schools at cap may accumulate inactive students; automated archival mitigates this
- Negative: Less urgency to upgrade — some schools may delay conversion indefinitely
