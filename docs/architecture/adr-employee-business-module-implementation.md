# Employee Business Module — Architecture Decision Record

> **Status:** Final
> **Version:** 1.0
> **Last Updated:** 2026-08-30
> **Author:** AI (grill session with product owner)
> **Source:** `employee_business_module_prd.md`; `adr-student-employee-domain-implementation.md`; `adr-c02-identity-person-model-revamp.md`; backend surface map (migrations 001–023)
> **Purpose:** Define the Employee business module as the employment foundation — a first-class business resource (not an authenticated actor) that Teacher, Payroll, Leave, and HR build on — and record every implementation decision required before it is fed to sdd-stack.
> **Cross-References:**
> - [Student & Employee Domain Model — ADR](./adr-student-employee-domain-implementation.md) — D10 (employee lifecycle) amended here; D7 (`employee_profile`) deferred here
> - [C-02 Identity Person-Model Revamp — ADR](./adr-c02-identity-person-model-revamp.md) — `person` entity + `person_id` link this module depends on
> - [C-02 Identity & User Management — ADR](./adr-c02-identity-user-management-implementation.md) — account lifecycle, cascade target
> - [C-04 Authorization Consolidation](../../openspec/specs/authorization/spec.md) — AuthZ Kernel + Casbin + RLS
> - [Architecture v1](./architecture-v1.md)

---

## 1. Context

The platform's people-centric modules (C-01 Tenant/Institution, C-02 Identity, C-03 Auth, C-04 Authz, C-05 Academic Structure, C-08 Config, Fees, Homework) are built, and the identity side has been revamped around a `person` entity (person-model-revamp ADR). The domain-split ADR (grill #1) already decided that `student` and `employee` are **first-class domain entities** (Camp B) with an optional link to a login via `person` — but the `employee` table has **not** been created yet.

This ADR records the decisions for the **Employee business module** — the employment half of that domain split, expanded into a complete business module. It must:

1. Establish a stable employment identity (`employee`) independent of login accounts.
2. Reconcile the PRD's model with the already-decided ADRs (notably the employee lifecycle in domain-split D10, which the PRD's §12 contradicted).
3. Fix the exact employment taxonomy, reference data, numbering, lifecycle, API, authorization, and module placement — every open implementation question — so the module can be fed to sdd-stack without further decisional ambiguity.

Employee is the foundation for Teacher, Leave, Payroll, HR, Performance, and Benefits — but this module deliberately does **not** absorb any of those downstream responsibilities (the PRD's §6 non-goals stand).

---

## 2. Decision

| # | Decision | Choice | Rationale |
|---|---|---|---|
| **D1** | **Employee lifecycle (7 states)** | `Hired → Active ↔ On-Leave → Retired \| Resigned \| Terminated`, plus `Suspended` (reversible to `Active`). `Onboarding` is **dropped for v1**. | **Amends domain-split D10** (`Hired→Onboarding→Active→On-Leave→Resigned\|Terminated`). Adds `Retired` (a real terminal state distinct from resignation/termination) and `Suspended` (disciplinary). Drops `Onboarding` — a state with no entry point in the v1 API and no consumer (YAGNI; the PRD never listed it). `Active ↔ On-Leave` stays reversible (sabbatical/maternity/medical); the terminal trio is irreversible. |
| **D2** | **`Suspended` representation** | A **distinct `employment_status` value**, reversible back to `Active` — not a boolean flag on `Active`. | Directly queryable/filterable (`WHERE employment_status = 'Suspended'`, PRD §33). A suspended employee is excluded from assignment by a single field check, mirroring how `On-Leave` already works. |
| **D3** | **Employment-type storage** | Python `StrEnum` in code + a `CHECK (employment_type IN (...))` constraint on the column. **Not** config, **not** a lookup table. | Employment type is a *stable product-wide taxonomy*, not institution-varying *behavior*. Config keys are right for things like `fee.lateFeePercentage` (per AGENTS.md §8), not for a fixed HR taxonomy. The codebase already enforces domain enums this way (`person.status` uses a `CheckConstraint`). |
| **D4** | **Employment-type values** | `FULL_TIME, PART_TIME, CONTRACT, TEMPORARY, INTERN, CONSULTANT` (all six, kept as-is). | Each has distinct payroll/leave implications downstream; none are collapse-worthy despite `CONTRACT`/`TEMPORARY`/`CONSULTANT` being cousins. |
| **D5** | **Department & designation** | **Config-driven allowed-values lists**: `employee.departments` and `employee.designations` (JSON-list config keys seeded via C-08). The employee column stores the chosen string; the API validates against the list. | Department/designation are *institution-varying reference data*, unlike employment type. Config lists give validated, filterable, institution-customizable values and reuse C-08's editing surface — no new lookup tables or CRUD. Tradeoff: validation is application-level (config cannot enforce a DB check), which is acceptable. |
| **D6** | **Employee number** | `employee_no`, auto-generated per institution as `EMP-{inst_code}-{seq:06d}`, `NOT NULL`, unique within institution. Reuses the fees `get_next_receipt_number` `with_for_update()` pattern. | Follows the existing per-institution sequence convention (PRD §10 forbids a new Identifier Generation Kernel). `NOT NULL` + unique-within-institution gives the stable business identifier. Manual entry and override are deferred (no v1 payoff). |
| **D7** | **Extended profile** | **Defer `employee_profile`.** This module builds only the core `employee` table. The domain-split D7 constraint is preserved: when qualifications/certs/employment-history land, they go in a separate `employee_profile` table, never as columns on `employee`. | No current consumer needs extended HR data (HR is a future module); building it now is speculative. The core table is what Teacher/Payroll/Leave need first. |
| **D8** | **Cross-institution employment** | **One `employee` row per (person, institution)**, enforced by `UNIQUE(person_id, institution_id)`. A person employed at two institutions = two `employee` rows, each with its own `employee_no` and lifecycle. | Mirrors person-model-revamp D3b (one `app_user` per institution) on the employment side. `employee` already carries `person_id NOT NULL` + `institution_id NOT NULL`; the composite unique falls out naturally. A person can't hold two employment relationships in the *same* institution. |
| **D9** | **Cascade to login** | Terminal transitions `Resigned`/`Terminated`/`Retired` auto-archive the linked `app_user` account **whose `institution_id` matches the employee's institution**, through the `person` link, in the same transaction. No cascade for `Suspended`/`On-Leave` (reversible). | Extends domain-split D12 to cover `Retired` and makes the cascade **institution-scoped** (correct under D8 — resigning from Institution A must not archive the Institution B account). Unconditional; the config-gated cascades are student-only. |
| **D10** | **Config keys** | Exactly two: `employee.departments` and `employee.designations` (both JSON-list, institution-scoped), seeded via C-08 migration and documented in `employee/manifest.py`. | Per AGENTS.md §8 (config-first). The `EMP-` number prefix is hardcoded (like fees' `REC-`); cascade is unconditional; initial status is a code default. No other institution-customizable behavior identified. |
| **D11** | **API surface** | `POST /employees` (create → `Hired`); `GET /employees` (list); `GET /employees/{id}`; `PATCH /employees/{id}` (edit department/designation/type/joining_date); plus four transition endpoints: `activate` (`→ Active` from any non-terminal reversible state), `suspend` (`Active → Suspended`), `deactivate` (`Active → On-Leave`), `terminate` (`Active → Terminated\|Resigned\|Retired` via a `terminal_status` body field). | Each transition maps to a distinct authz capability (PRD §49). `activate` doubles as "return to active" (Suspended/On-Leave → Active), so no separate `resume`. The three terminal states collapse into one `terminate` endpoint (all terminal + cascade identically, D9). Domain enforces valid transitions. |
| **D12** | **Authorization matrix** | Seven `employee.*` permissions, institution scope: `create, read, update, activate, suspend, deactivate, terminate`. Default seed: **Admin / InstituteAdmin / Staff = full set; HOD / Principal / Teacher = `read`; PlatformOwner = none.** | Employee is a protected business resource; the authenticated `User` is the AuthZ subject (PRD §2/§17). No hardcoded role checks — uses `require_permission("employee", "<action>")`. PlatformOwner gets no operational-employee access (PRD §21). Teacher's self-scoped read is future ABAC, not now (PRD §19). Exact role→permission tuning is seed data. |
| **D13** | **`Onboarding` state** | **Dropped for v1** (folded into D1's 7-state lifecycle). Reintroduce when the HR module needs it. | A state with no API entry point and no v1 consumer; keeping it would be complexity without a consumer. |
| **D14** | **Module placement & structure** | `backend/business/employee/` with the existing convention: `manifest.py`, `dependencies.py`, `models/`, `repos/`, `routes/`, `services/`. **Not** the PRD's `domain/application/infrastructure` DDD layout. | Employee depends on Kernel (person, AuthZ, config, tenant context) and is depended on by future modules — so it is a *business* module (like fees/homework). The PRD's DDD layout does not match the codebase; the PRD's principles (thin controllers, domain rules out of endpoints, no framework deps in domain) are honored *inside* the models/repos/routes/services layout: enums + lifecycle validation in `models/`, orchestration in `services/`, controllers thin. |

---

## 3. Consequences

**Positive:**
- **One unambiguous model** — the PRD's contradictions with the domain-split ADR (lifecycle) and with the codebase (DDD layout, naming) are resolved before any sdd-stack work begins.
- **Employee is a true business resource** — employment identity is decoupled from login identity, sits on the `person` anchor, and survives login archival (ex-employees keep their record).
- **Employment taxonomy is principled**: fixed product-wide values → code enum (`employment_type`); institution-varying reference data → config keys (`department`, `designation`). This line is reusable for future modules.
- **Minimal surface** — seven states, seven permissions, six endpoints, two config keys, one table. No speculative `employee_profile`, no `Onboarding`, no identifier-generation kernel, no lookup tables.
- **Cross-institution correct** — the `UNIQUE(person_id, institution_id)` + institution-scoped cascade mirror the account model, so a multi-school teacher resolves cleanly.
- **AuthZ pipeline untouched** — roles stay on the account; Employee is a resource evaluated through the existing `require_permission` + Casbin + RLS path.

**Negative / cost:**
- **Two ADRs amended at the boundaries** — D1 amends domain-split D10 (lifecycle) and D7 (deferral) is recorded; implementers must read both. The `teacher_assignment.teacher_id → app_user.id` FK (C-05) will need a repoint when the Teacher module lands (deferred, not this module).
- **Application-level validation for department/designation** — config lists can't enforce a DB constraint; consistency depends on the API validating against C-08.
- **`Hired` as the sole pre-active state** — schools that want a formal onboarding/paperwork stage in v1 will have to wait for the HR module.

---

## 4. Model

```
                         IDENTITY (kernel/user)                 BUSINESS (business/employee)
   ┌─────────────────────────────────────────────┐    ┌─────────────────────────────────────────────┐
   │ person                                      │    │ employee                                    │
   │  id (PK)                                    │◄───│  id (PK)  ── employee_id                   │
   │  name, dob, gender, contact, demographics   │  1 │  client_id → client.id (NOT NULL)          │
   │  status (Active|Inactive|Deceased|…)        │ :  │  institution_id → institution.id (NOT NULL)│
   └──────────────┬──────────────────────────────┘  N │  person_id → person.id (NOT NULL)          │
                  │ 1:N                                │  employee_no (auto EMP-{inst}-{seq:06d},  │
                  ▼                                    │   NOT NULL, unique within institution)     │
   ┌──────────────────────────────┐                   │  joining_date                               │
   │ app_user  (inst account)     │                   │  employment_type (enum, CHECK)             │
   │  person_id → person.id       │                   │  employment_status (enum, 7 states)        │
   │  institution_id (NOT NULL)   │                   │  department  (validated vs config list)    │
   │  lifecycle (invited→archived)│                   │  designation (validated vs config list)    │
   └──────────────────────────────┘                   │  created_at, updated_at                     │
                                                      │  UNIQUE(person_id, institution_id)          │
                                                      └──────────────┬──────────────────────────────┘
                                                                     │ 1:N (future, DEFERRED)
                                                                     ▼
                                                        ┌──────────────────────────────┐
                                                        │ employee_profile (deferred)  │
                                                        │  qualifications, certs,       │
                                                        │  employment history           │
                                                        └──────────────────────────────┘

   LIFECYCLE (D1):
     Hired ──activate──► Active ◄──activate── Suspended
                            │  ▲
                deactivate  │  │  activate
                            ▼  │
                        On-Leave
                            │
        ┌───────────────────┼───────────────────────┐
        ▼                   ▼                       ▼
     Retired            Resigned               Terminated
        └────(all terminal: cascade → archive app_user, D9)────┘

   API (D11):
     POST   /employees                     → create (status = Hired)
     GET    /employees                     → list (filter: status, type, department, designation, search, pagination)
     GET    /employees/{id}                → get
     PATCH  /employees/{id}                → edit fields
     POST   /employees/{id}/activate       → Hired/Suspended/On-Leave → Active
     POST   /employees/{id}/suspend        → Active → Suspended
     POST   /employees/{id}/deactivate     → Active → On-Leave
     POST   /employees/{id}/terminate      → Active → Terminated|Resigned|Retired  (body: terminal_status)

   CONFIG (D10, C-08):
     employee.departments    = ["Administration", "Mathematics", "Accounts", "Library", …]
     employee.designations   = ["Teacher", "Accountant", "Librarian", "Receptionist", …]

   AUTHZ (D12, scope = institution):
     employee.create / read / update / activate / suspend / deactivate / terminate
     Admin|InstituteAdmin|Staff → full set; HOD|Principal|Teacher → read; PlatformOwner → none
```

---

## 5. Constraints

1. **Employee is a business resource, never an authenticated actor.** AuthZ evaluates requests made by authenticated `User`s; Employee is the protected resource (PRD §2). Employee never authenticates and never passes through AuthZ independently.
2. **Employee links to `person`, never to an account.** `employee.person_id NOT NULL` (a domain entity must know which human it projects). The `IdentityDomainLinkingService` resolves account↔domain through `person`.
3. **One employment relationship per (person, institution).** `UNIQUE(person_id, institution_id)`; cross-institution employment is multiple `employee` rows, mirroring the account model (D3b).
4. **`employment_status` values are fixed (7 states)** and enforced by a DB `CHECK` constraint. Only the transitions in D1 are valid; the domain must reject invalid transitions (e.g. `Terminated → Active`).
5. **`employment_type` values are fixed (6 values)** and enforced by a DB `CHECK` constraint. No institution-customizable employment types in v1.
6. **Department/designation are config-driven**, validated against `employee.departments` / `employee.designations` at the API/application layer. They are labels only — `designation = 'Teacher'` must **not** create a Teacher entity (Teacher is a future module).
7. **Extended employee data goes in a future `employee_profile` table, never on `employee`** (domain-split D7). This module does not build it.
8. **Terminal transitions cascade to the institution-matching account** via `person` (D9), in the same transaction. Resigning from Institution A archives only the Institution A account.
9. **No hardcoded role checks.** All operations use the AuthZ Kernel (`require_permission("employee", …)`); no Platform Owner bypass for operational employee data.
10. **PostgreSQL RLS protects `employee`** as defense-in-depth, following the `person`/fee RLS pattern (tenant-scoped policies; application authz does not replace RLS).
11. **Follow the existing module convention** (D14): `models/ repos/ routes/ services/ dependencies.py manifest.py` under `business/employee/`. No DDD folder layout, no new generic repository framework, no new identifier-generation kernel.
12. **Disposable-DB assumption applies.** This module's migration is schema + reseed + tests; no backfill of existing `app_user` rows into `employee` is required (there are none).
13. **Config keys are seeded via C-08 migration and documented in `manifest.py`** (AGENTS.md §8), never via editing existing seed data.

---

## 6. Alternatives Considered

| Alternative | Reason for Rejection |
|---|---|
| **PRD §12's six-status model** (`ACTIVE/ON_NOTICE/SUSPENDED/INACTIVE/TERMINATED/RETIRED`). | Contradicted the already-decided domain-split D10; `ON_NOTICE`/`INACTIVE` were redundant, `SUSPENDED` lacked `On-Leave`'s distinction. Reconciled to D1 instead (D10 amended, `Retired`+`Suspended` added). |
| **`Suspended` as a boolean flag on `Active`** (vs D2 distinct value). | A composite `Active AND NOT is_suspended` check is messier for assignment/leave exclusion and not directly filterable as a status. |
| **Employment type as config key or lookup table** (vs D3 enum). | Employment type is a fixed taxonomy, not institution-varying behavior (config) or high-cardinality reference data (lookup). A lookup table over-normalizes six fixed values. |
| **Department/designation as free-text or lookup tables** (vs D5 config lists). | Free-text drifts ("Math" vs "Mathematics") and breaks filtering; lookup tables add two tables + CRUD + seeding for marginal benefit over config lists. |
| **Manual or hybrid employee number** (vs D6 auto-generate). | Manual entry adds a validation/duplicate-check surface with no v1 payoff; hybrid adds an override path that can be bolted on later. Auto-generation reuses the existing receipt-number pattern. |
| **Include `employee_profile` now** (vs D7 defer). | Speculative — no current consumer of qualifications/certs/employment-history. |
| **One `employee` row per person, membership elsewhere** (vs D8). | Re-introduces a person→institution link outside `employee`; the `UNIQUE(person_id, institution_id)` + row-per-institution model mirrors the account side cleanly. |
| **Keep `Onboarding` and wire it in** (vs D13 drop). | A two-step `activate` or a separate `onboard` endpoint with no v1 consumer; YAGNI. |
| **DDD folder layout** (`domain/application/infrastructure`, PRD §30) (vs D14 existing convention). | Does not match the codebase's `models/repos/routes/services` convention; introduces a second architectural style for one module. |

---

## 7. Future Evolution

- **Teacher module (next academic capability)** will add a `teacher` entity referencing `employee.id`, then repoint `teacher_assignment.teacher_id` from `app_user.id` → `employee.id` (via `teacher`). This module delivers the clean `employee` anchor for that repoint.
- **Payroll / Leave / HR** reference `employee.id` and consume `employment_type` + `employment_status`, without adding salary/leave-balance/workflow fields to `employee`.
- **`employee_profile`** (qualifications, certifications, employment history) is added as a separate table when HR/recruitment needs it (domain-split D7).
- **`Onboarding` reintroduction** if a formal onboarding/paperwork stage becomes a real requirement (revisit D1/D13).
- **Custom employment types** — if an institution genuinely needs a non-standard type, promote `employment_type` from enum to config (the D3/D5 line shows the upgrade path).
- **Teacher self-scoped `employee.read` via ABAC** (`is_subject_teacher`-style attributes) when the Teacher domain lands; not part of this module (PRD §19).
- **Non-disposable migration path** — once real data lands, the clean-cut pattern must be replaced by proper backfill for any further `employee` schema change.
