# Architecture — Index

> **Folder:** `docs/architecture/`  
> **Purpose:** Architectural decisions, principles, models, and constraints.

---

## Documents

| File | Version | Status | Description |
|---|---|---|---|
| `architecture-v1.md` | 1.0 | ✅ Final | Core architecture: tenant model, data isolation, modular monolith, platform principles |
| `adr-platform-tech-stack.md` | 1.0 | ✅ Final | ADR: platform-wide tech stack (Postgres/Supabase, Python/FastAPI, SQLAlchemy 2.0 + Alembic, Supabase Auth, Casbin, pytest). Unblocks C-01 apply. |
| `adr-platform-software-architecture.md` | 1.0 | ✅ Final | ADR: modular monolith (kernel/shared/business tiers, dependency law, module-manifest composition, hybrid Depends+contextvar integration, single Alembic env) + frontend direction (Vite+React SPA web-first, native-later, monorepo, TanStack Query+Zustand). |
| `adr-c01-tenant-institution-implementation.md` | 1.0 | ✅ Final | ADR: 12 implementation decisions for C-01 (isolation, IDs, slug, schemas, lifecycles, OrgUnit↔C-05 boundary, permissions, ownership transfer) |

## Upcoming Documents

| Document | Description |
|---|---|
| `database-schema.md` | Entity-relationship model per capability |
| `security-architecture.md` | Security model, encryption, data protection |
| `api-guidelines.md` | API design standards, versioning, pagination |

---

> **Note:** Architecture decisions must be recorded before implementation begins. Each decision should follow the ADR template in `docs/reference/document-template.md`.
