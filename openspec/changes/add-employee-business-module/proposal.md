## Why

The Employee module establishes the employment relationship as a first-class business resource — the foundation that Teacher, Leave, Payroll, HR, Performance, and Benefits will build on. Today there is no `employee` table: people are still modeled as `app_user` rows, which breaks the moment employment outlives a login (ex-employees keep records; cross-institution staff need one human identity). The domain-split ADR already decided `employee` is a first-class domain entity; this change implements the employment half of that split as a complete business module.

## What Changes

- New `employee` table in a new `business/employee/` module (models/repos/routes/services + manifest), linking to `person` (NOT `app_user`).
- Employment lifecycle: `Hired → Active ↔ On-Leave → Retired | Resigned | Terminated`, plus `Suspended` (reversible) — 7 states, enforced by domain transition rules and a DB check.
- Employment type: fixed enum `FULL_TIME / PART_TIME / CONTRACT / TEMPORARY / INTERN / CONSULTANT`.
- Department & designation: config-driven lists (`employee.departments`, `employee.designations`) seeded via C-08, validated at the API layer.
- Auto-generated `employee_no` (`EMP-{inst_code}-{seq:06d}`), unique per institution, reusing the fees receipt-number pattern.
- Employee API: create/list/get/patch + `activate`/`suspend`/`deactivate`/`terminate` transition endpoints.
- Authorization: 7 new `employee.*` permissions (create/read/update/activate/suspend/deactivate/terminate), institution scope; Admin/InstituteAdmin/Staff = full set, HOD/Principal/Teacher = read, PlatformOwner = none.
- Cascade: terminal transitions archive the institution-matching `app_user` account (via `person`, same transaction).
- PostgreSQL RLS on `employee` (tenant-scoped), following the existing `person`/fee pattern.

## Capabilities

### New Capabilities
- `employee`: the employee business module — employment identity, lifecycle, employment type/status, department/designation reference data, auto-generated employee number, API, authorization, and RLS.

### Modified Capabilities
<!-- No existing capability's spec-level behaviour changes. New `employee.*` permissions are C-04 seed data, not a change to the AuthZ Kernel's evaluation behaviour. -->

## Impact

- **New code**: `backend/business/employee/` (models, repos, routes, services, dependencies, manifest).
- **New migration**: `employee` table + check constraints + `UNIQUE(person_id, institution_id)` + indexes + RLS policies; seed `employee.departments` / `employee.designations` config keys; seed 7 `employee.*` permissions + role_permission mappings.
- **Dependencies**: reads `person` (kernel/user), AuthZ Kernel (kernel/authz), config (kernel/config), tenant context (kernel/tenant_context). No changes to existing business modules.
- **Deferred (out of scope)**: `employee_profile` table, `Onboarding` state, Teacher/Payroll/Leave/HR modules, `teacher_assignment.teacher_id` repoint.
