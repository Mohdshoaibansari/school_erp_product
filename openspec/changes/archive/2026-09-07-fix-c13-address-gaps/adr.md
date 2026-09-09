# ADR Review Manifest

- Status: completed
- Review date: 2026-09-08

## Review Summary

ADR review completed for change `fix-c13-address-gaps`. This is a hardening delta on C-13 Address Management; it reuses durable decisions from D1-D15 locked 2026-09-07 (Gap Register §710 / PRD §24). No divergent durable architectural commitments are introduced that would supersede an in-force repo-level ADR.

Pending docs-first action: `docs/prd/C-13-Address-Management-PRD.md` §7 `postal_code No → Yes` amendment (confirmed 2026-09-07, per `AGENTS.md §3 Change Loop`). Tracked as a PRD amendment, not a new repo-level ADR.

## In-Force ADRs Reviewed

- `docs/architecture/adr-c01-tenant-institution-implementation.md` — D1 tenant isolation (repo + RLS defense-in-depth), `client_id`/`institution_id` scope model; C-13 derives scope from target entity — coherent.
- `docs/architecture/adr-c02-identity-user-management-implementation.md` — Identity & User Management baseline; `PERSON` EntityType maps to C-02 Person.
- `docs/architecture/adr-c02-identity-person-model-revamp.md` — Person-model revamp (D3a–D3e, D6a); PERSON EntityType remains `PERSON` code.
- `docs/architecture/adr-c05-academic-structure-implementation.md` — Academic Structure (archived) — boundary unaffected.
- `docs/architecture/adr-frontend-implementation.md` — Frontend (archived) — no C-13 UI contract change beyond address CRUD wiring.
- `docs/architecture/adr-student-employee-domain-implementation.md` (v1.1) — Student & Employee domain model; both via `PERSON` EntityType (D2) — coherent, no new Student/Employee EntityType.
- No repository-level ADRs found under `adr/` (top-level) — checked; none in force to supersede.

All reviewed ADRs remain in force. D1-D15 are intentionally recorded in `docs/prd/C-13-Address-Management-PRD.md §24` and `C-13-Address-Management-Gap-Register-and-Implementation-Plan.md` and consumed by `design.md`; they do not establish a new cross-capability technology, pattern, or boundary beyond the archived C-13 ADR context.

## New Durable ADRs Created

- None - no major durable architectural decisions were introduced.

## Notes

- **Decision not to create a repo-level ADR:** The durable commitments for this fix are the existing D1-D15. This change tightens enforcement (code-based resolution, `UNIQUE(address_id)`, `postal_code NOT NULL`, temporal/transactional guarantees, hierarchy on all write paths, audit via `AuditEmitter`) but does not introduce a new long-lived pattern/technology/boundary that would affect future changes beyond C-13. A repo-level ADR would duplicate PRD §24 / Gap Register §710 without adding a cross-cutting decision.
- **If a future change introduces** RLS on C-13, geospatial expansion, or a new generic polymorphic usage beyond addresses, a repository-level ADR SHALL be created at that time and SHALL supersede the applicable section of `adr-c01-tenant-institution-implementation.md` if scope diverges.
