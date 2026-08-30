## Context

The platform is a modular monolith (FastAPI + SQLAlchemy 2.x + PostgreSQL/Supabase + Alembic). Identity (C-02) was recently revamped around a `person` entity; accounts (`app_user`/`client_user`) are thin, and roles stay on accounts (D8/D3b). Authorization (C-04) is a Casbin-backed AuthZ Kernel with a `permission`/`role_permission` DB model and PostgreSQL RLS as defense-in-depth. Existing business modules (fees, homework) follow a `models/ repos/ routes/ services/ dependencies.py manifest.py` layout under `business/`.

This change adds the Employee business module (`business/employee/`), the employment half of the already-decided domain split. The durable decisions are recorded in `docs/architecture/adr-employee-business-module-implementation.md` (D1–D14); the behavioral contract is in `specs/employee/spec.md`.

## Goals / Non-Goals

**Goals:**
- Stand up the `employee` table + module, linked to `person` (not `app_user`).
- Implement the 7-state lifecycle with domain-validated transitions and terminal→account cascade.
- Expose the minimal API (create/list/get/patch + activate/suspend/deactivate/terminate).
- Wire 7 `employee.*` permissions + default role seed + RLS.
- Seed the two config keys (`employee.departments`, `employee.designations`).

**Non-Goals:**
- No `employee_profile` table (deferred, domain-split D7).
- No `Onboarding` state (deferred, ADR D13).
- No Teacher/Payroll/Leave/HR logic; no `teacher_assignment.teacher_id` repoint.
- No new identifier-generation kernel, no lookup tables, no event bus.

## Decisions

All decisions trace to ADR D1–D14. Key technical choices and rationale:

1. **`employee` links to `person`, not `app_user`** (D3a/D1) — `person_id NOT NULL`, resolved via `IdentityDomainLinkingService`. Employment survives login archival.
2. **Composite unique `(person_id, institution_id)`** (D8) — one employment relationship per person per institution; cross-institution employment is multiple rows.
3. **Lifecycle as a domain state machine** (D1/D2/D9/D11) — 7 states enforced by a `CHECK` + domain transition validation in `models/`; `Suspended` is a distinct value, not a flag; terminal transitions cascade to the institution-matching account.
4. **Employment type = `StrEnum` + `CHECK`** (D3/D4) — fixed taxonomy; department/designation = config-driven lists validated in the service layer (D5).
5. **Auto-generated `employee_no`** (D6) — `EMP-{inst_code}-{seq:06d}` via a `with_for_update()` max-read, mirroring `fees.get_next_receipt_number`.
6. **Thin controllers + orchestration in services** (D14) — enums + transition rules in `models/`, repository (incl. number generator) in `repos/`, use-cases in `services/`, FastAPI routes use `require_permission("employee", …)`.
7. **AuthZ via the Kernel, no hardcoded role checks** (D12) — 7 `employee.*` permissions, institution scope; PlatformOwner gets none.
8. **RLS tenant-scoped** (D10 constraint) — `client_id`/`institution_id` policies matching the `person` table pattern.

### C4 — Container level (modular monolith)

```
┌──────────────┐        ┌─────────────────────────────────────────────────────────┐
│  Auth'd User │        │  FastAPI App (modular monolith)                         │
│  (app_user)  │───────►│                                                         │
└──────────────┘  HTTP  │  ┌───────────────┐   ┌───────────────────────────────┐  │
                        │  │ kernel/user   │   │ business/employee (NEW)        │  │
┌──────────────┐        │  │  person,      │◄──│  models  repos  routes         │  │
│  Platform    │        │  │  app_user     │   │  services  manifest            │  │
│  Owner (JWT) │───────►│  └───────┬───────┘   └──────────────┬────────────────┘  │
└──────────────┘  HTTP  │          │ FK: employee.person_id    │                  │
                        │  ┌───────▼───────┐   ┌───────────────▼───────────────┐  │
                        │  │ kernel/authz  │   │ kernel/config (C-08)          │  │
                        │  │ Casbin +      │   │  employee.departments,        │  │
                        │  │ permissions   │   │  employee.designations        │  │
                        │  └───────┬───────┘   └───────────────────────────────┘  │
                        │          │ require_permission("employee", ...)          │
                        └──────────┼──────────────────────────────────────────────┘
                                   ▼
                        ┌───────────────────────┐
                        │ PostgreSQL / Supabase │
                        │  person, app_user,    │
                        │  employee (NEW + RLS) │
                        │  permission/role_perm │
                        └───────────────────────┘
```

## Risks / Trade-offs

- [Department/designation are application-validated, not DB-enforced] → the service layer MUST validate against C-08 config; add a regression test for a value outside the list.
- [Auto-numbering concurrency] → use `with_for_update()` (SELECT … FOR UPDATE) as fees does; uniqueness backstop is the `(institution_id, employee_no)` unique index.
- [Cascade touches the account via person] → keep it same-transaction; test the multi-account scoping case (D9).
- [RLS must be added at the same time as the table] → migration enables + forces RLS before any seed insert reads/writes.

## Migration Plan

1. New Alembic migration: create `employee` table + `CHECK` constraints (status, type) + `UNIQUE(person_id, institution_id)` + `UNIQUE(institution_id, employee_no)` + indexes + RLS policies + grants.
2. Seed `employee.departments` / `employee.designations` config keys (C-08) in the same migration.
3. Seed 7 `employee.*` permissions + `role_permission` rows (Admin/InstituteAdmin/Staff full, HOD/Principal/Teacher read).
4. Update `scripts/seed_data.py` to seed a sample employee (disposable-DB assumption; no backfill).
5. Rollback: standard Alembic `downgrade` (drop policies → drop table → delete permissions → delete config keys).

## Open Questions

- None blocking. The `teacher_assignment.teacher_id → app_user.id` repoint is explicitly deferred to the Teacher module (flagged, not resolved here).
- The `adr/` convention in the intent-driven schema targets a repo-root `adr/` folder, but this repository's durable ADRs live in `docs/architecture/`. The durable ADR for this change is `docs/architecture/adr-employee-business-module-implementation.md`; no new repo-root `adr/` files are created.
