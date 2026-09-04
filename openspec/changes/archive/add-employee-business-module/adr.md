# ADR Review Manifest

- Status: completed
- Review date: 2026-08-30

## Review Summary

ADR review completed for this change. This repository's durable ADRs live in `docs/architecture/` (per `AGENTS.md` §7 and `docs/reference/document-template.md` §2), not a repo-root `adr/` folder. The durable decision record for this change is `docs/architecture/adr-employee-business-module-implementation.md` (D1–D14), authored in the grill session before OpenSpec and committed at `bede359`.

## In-Force ADRs Reviewed

The following in-force repository-level ADRs constrain this change and were reviewed for coherence:

- `docs/architecture/adr-student-employee-domain-implementation.md` — domain split (Camp B); D10 (employee lifecycle) is **amended** here; D7 (`employee_profile`) is **deferred** here.
- `docs/architecture/adr-c02-identity-person-model-revamp.md` — `person` entity + `person_id` link (D3a/D3b/D3f); the `employee` table links to `person`, not `app_user`.
- `docs/architecture/adr-c02-identity-user-management-implementation.md` — account lifecycle and cascade target.
- `docs/architecture/adr-c01-tenant-institution-implementation.md` — client/institution tenancy and isolation.
- `docs/architecture/adr-c05-academic-structure-implementation.md` — `teacher_assignment` currently FKs `app_user.id`; the eventual repoint to `employee` is deferred to the Teacher module.
- `docs/architecture/adr-platform-software-architecture.md` and `adr-platform-tech-stack.md` — modular monolith, FastAPI/SQLAlchemy 2.x/PostgreSQL/Alembic, AuthZ Kernel + Casbin, RLS.

## New Durable ADRs Created

- `docs/architecture/adr-employee-business-module-implementation.md` — records the 14 implementation decisions (D1–D14) for the Employee business module. This is the durable decision record; its full Context / Decision / Consequences / Model / Constraints / Alternatives / Future Evolution content is not duplicated here.
