# User Journey Map — School ERP Platform

> **Date:** 2026-08-14
> **Scope:** All 11 implemented roles
> **Includes:** Success paths + failure scenarios (wrong tenant, wrong role, missing permissions, invalid data)

---

## Roles Overview

| Role | Tier | Scope | # Permissions |
|---|---|---|---|
| Platform Owner | Platform | Any (code bypass) | 8 (config) + wildcard |
| Client Director | Client | Own client (tenant) | 47 |
| Institution Admin | Institution | Own institution | 10 |
| Admin | Institution | Own institution | 39 |
| Principal | Institution | Own institution | 18 |
| HOD | Institution | Own institution | 10 |
| Teacher | Institution | Own institution | 12 |
| Staff | Institution | Own institution | 3 |
| Student | Institution | Own institution | 7 |
| Parent | Institution | Own institution | 1 |
| Cross-institution | Client | Own client (read-only) | 3 |

## Journey Files

| File | Role | Coverage |
|---|---|---|
| `01_platform_owner.md` | Platform Owner | Client CRUD, institution types, config, ownership transfer |
| `02_client_director.md` | Client Director | Institution CRUD, org units, user management, fees, profiles |
| `03_institution_admin.md` | Institution Admin | Institution update, org units, profile management |
| `04_admin.md` | Admin | Full institution management, users, fees, config |
| `05_principal.md` | Principal | Read-most, org unit management |
| `06_hod.md` | HOD | Read-most, org unit update |
| `07_teacher.md` | Teacher | Homework, grades, own profile |
| `08_staff.md` | Staff | Limited — user read, own profile |
| `09_student.md` | Student | Homework view, submissions, grades |
| `10_parent.md` | Parent | Read-only — user read |
| `11_cross_institution.md` | Cross-institution | Read-only — client, institution, org_unit |
| `12_failure_scenarios.md` | All roles | Cross-tenant, cross-role, invalid data, lifecycle blocks |
