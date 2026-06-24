# 0005. Student lifecycle billing based on active enrollment

- Status: accepted
- Date: 2026-06-20

## Context

Per-student billing requires defining what counts as a billable student. Options: all student records (including alumni and archived), only actively enrolled students, or only students with activity in the billing period. Billing for inactive students is unfair. Billing by activity is complex to measure. Billing by enrollment status is clean and auditable.

## Decision

Only actively enrolled students count toward billing. A student is active when they have an active enrollment in the current academic year. Students who graduate become "alumni" and stop counting. Students inactive for 2+ consecutive academic years are auto-archived and stop counting. Transferred students stop counting for the source institution. Alumni and archived students are managed as a separate read-only record set.

## Consequences

- Positive: Billing aligns with actual usage — schools pay for students they're actively educating
- Positive: Clear, auditable definition — enrollment status is an objective system state
- Neutral: Requires precise enrollment lifecycle management — bugs affect billing accuracy
- Negative: Schools may retain inactive students on enrollment to inflate counts; automated archival mitigates this
