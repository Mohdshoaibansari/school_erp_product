# Business Modules

Business modules are **domain-level capabilities** that implement educational workflows. They depend on the Platform Kernel (kernel infrastructure packages under `kernel/`) and may depend on other business modules. Unlike kernel infrastructure (which every module imports), business modules contain domain logic used only by their own workflows.

## C-01b: Tenant & Institution Domain

> **Status:** Built (apply phase complete, 167 tests)
> **Location:** `business/tenant_institution/`

Owns the lifecycle and relationships of Clients, Institutions, and OrgUnits. Provides:

- **Client CRUD + lifecycle state machine** (Prospect → Active → Suspended → Terminated)
- **Institution CRUD + lifecycle** (Onboarding → Active → Inactive → Archived) with runtime effective-state gating
- **OrgUnit hierarchy** (adjacency list, recursive CTE, cycle-prevented moves, archive-only soft-delete)
- **InstitutionType template materialization** (JSONB template → OrgUnit tree at institution creation)
- **Ownership transfer** (single-transaction Client A→B migration, consent + approval flow)
- **D11 Casbin permission matrix** (Platform Owner / Client Director / Institution Admin / Cross-Institution roles)

Depends on: `kernel/tenant_context.py`, `kernel/middleware.py`, `kernel/repo_base.py`, `kernel/audit.py`, `kernel/transfer_coordinator.py` (C-01a Tenant Identity Infrastructure).

## Future Business Modules

| ID | Module | Phase | Description |
|---|---|---|---|
| — | Attendance | 1 | Student attendance marking, reports, absence alerts |
| — | Homework | 1 | Assignment creation, submission tracking, grading |
| — | Fees | 1 | Fee plans, collection tracking, receipt generation |
| — | Exams | 1 | Exam scheduling, grading, report cards |
| — | Timetable | 1 | Class schedules, room allocation, teacher assignments |
| — | Parent Communication | 1 | Messaging, announcements, parent-teacher meetings |

See [Platform Capabilities v3](../platform-capabilities/platform-capabilities-v3.md) for the full capability catalog and classification matrix.
