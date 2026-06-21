## Why

School ERP market in India has hundreds of point solutions but no single platform that combines a modern SaaS architecture, per-student pricing, a generous free tier to drive adoption, and the ability to deploy dedicated instances for enterprise clients. Schools need attendance tracking, fee management, communication, and more — but most are small (under 500 students) and price-sensitive. Building a multi-tenant platform with a free tier removes the adoption barrier and lets schools grow into paid modules as their needs expand.

## What Changes

- Build a multi-tenant SaaS platform with row-level data isolation
- Free tier: Students, Attendance, Fees modules — up to 100 active students, soft block beyond
- Paid modules per student: Exams, Homework, Transport, Communication, Timetable, and others
- Per-student billing based on actively enrolled students (not alumni or archived)
- Paid clients get all modules — pricing is per-student, not per-module
- Hidden module gating (paid modules are invisible to free-tier users, not upsold)
- Single codebase, single deployment — dedicated instance option available on request
- Self-host option deferred — if isolation needed, deploy new SaaS instance

## Capabilities

### New Capabilities

- `subscription-billing`: Multi-dimensional subscription management tracking module entitlements, student seat limits, and per-student billing counts. Supports free tier caps, paid tier unlocks, and soft-block enforcement.
- `student-enrollment`: Active student lifecycle — enrollment, transfer, graduation, alumni separation. Tracks current enrollment status for billing purposes.
- `module-gating`: Frontend and API layer that hides unsubscribed modules entirely. No upsell UI, no disabled buttons — paid modules are invisible to free-tier users.

### Modified Capabilities

- `tenant-institution`: Extend C-01 to support subscription tier metadata per tenant. Track whether a client is free or paid, their student cap, and their billing status.
- `identity-users`: Track student lifecycle status (active, graduated, transferred, archived) per enrollment. Only actively enrolled students count toward billing.
- `configuration`: Add C-08 feature flags driven by subscription tier rather than manual configuration. Module availability becomes data-driven from C-07.

## Impact

- C-07 Subscription Management becomes the most architecturally significant capability — it gates every module and enforces student caps
- Student enrollment lifecycle must be precise — billing depends on accurate active/inactive status
- Frontend must be subscription-aware — same build, different module visibility per tenant
- No separate self-host code path needed for now
- API layer needs subscription-enforcement middleware (reject POST/PUT for capped resources, allow reads)
