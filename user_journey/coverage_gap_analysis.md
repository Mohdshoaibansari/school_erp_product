# Journey Flow Coverage Gap Analysis

> **Date:** 2026-08-14
> **Compared:** `user_journey/*.md` vs `backend/static/journey_flows/*.html`

---

## Coverage Matrix

| Role | Journey Doc | Static Flow | Coverage |
|---|---|---|---|
| Platform Owner | `01_platform_owner.md` | `01`, `09`, `10`, `12`, `13` | ✅ Good |
| Client Director | `02_client_director.md` | `02`, `07`, `13`, `14`, `16` | ✅ Good |
| Institution Admin | `03_institution_admin.md` | `03`, `08` | ⚠️ Partial |
| **Admin** | `04_admin.md` | — | ❌ **Missing** |
| **Principal** | `05_principal.md` | — | ❌ **Missing** |
| **HOD** | `06_hod.md` | — | ❌ **Missing** |
| Teacher | `07_teacher.md` | `04` | ✅ Good |
| **Staff** | `08_staff.md` | — | ❌ **Missing** |
| Student | `09_student.md` | `05`, `14` | ✅ Good |
| Parent | `10_parent.md` | `06` | ⚠️ Partial |
| **Cross-institution** | `11_cross_institution.md` | — | ❌ **Missing** |
| Failure Scenarios | `12_failure_scenarios.md` | `07`, `08`, `11` | ⚠️ Partial |

---

## Missing Flows (5 roles + failure gaps)

### 1. Admin Flow — ❌ Not covered
**Journey:** `04_admin.md` — 13 happy paths, 5 failure scenarios
**What's missing:**
- Admin login
- Create user (Teacher, Student)
- List users
- Suspend user
- Create/list/update fee types
- Assign fees to students
- Record payments
- Create/update profiles for any user
- Create/delete role assignments
- Read/update config values
- Failure: can't create institution, can't access other institution, can't manage platform config, can't delete user

### 2. Principal Flow — ❌ Not covered
**Journey:** `05_principal.md` — 7 happy paths, 5 failure scenarios
**What's missing:**
- Principal login
- Read institution
- Update institution
- Create/delete org units
- List users (read-only)
- Read role assignments
- Failure: can't create user, can't manage fees, can't suspend user, can't read other profiles, can't manage config

### 3. HOD Flow — ❌ Not covered
**Journey:** `06_hod.md` — 7 happy paths, 4 failure scenarios
**What's missing:**
- HOD login
- List users (read-only)
- Read role assignments
- Update org unit
- Read fee assignments, homework, submissions
- Failure: can't create user, can't create homework, can't create fee type, can't read other profiles

### 4. Staff Flow — ❌ Not covered
**Journey:** `08_staff.md` — 5 happy paths, 5 failure scenarios
**What's missing:**
- Staff login
- List users (read-only)
- Update own profile
- Read own profile
- Read fee assignments
- Failure: can't create user, can't create homework, can't manage fees, can't read other profiles, can't manage org units

### 5. Cross-institution Flow — ❌ Not covered
**Journey:** `11_cross_institution.md` — 6 happy paths, 6 failure scenarios
**What's missing:**
- Cross-institution role login
- Read client info
- List institutions (cross-institution view)
- Read institution
- List org units (cross-institution)
- Failure: can't create/update institutions, can't create users, can't manage org units, can't manage fees, can't access other client

### 6. Failure Scenario Gaps
**Journey:** `12_failure_scenarios.md` — 27 scenarios
**What's missing from static site:**
- Profile failures (FP-01: duplicate profile, FP-02: teacher can't update other teacher, FP-03: student can't create other's profile)
- RLS failures (FRL-01: empty list when no data in scope, FRL-02: 404 for other-scope resource)
- Some cross-role failures (FR-01: teacher can't create fee type, FR-02: student can't create homework, FR-05: inst_admin can't create institution)

---

## Implementation Plan

### Phase 1: New Role Flows (5 new HTML files)
| # | File | Role | Steps |
|---|---|---|---|
| 1 | `17_admin.html` | Admin | Login → create user → list users → suspend user → manage fees → manage profiles → failure scenarios |
| 2 | `18_principal.html` | Principal | Login → read institution → update institution → manage org units → list users → failure scenarios |
| 3 | `19_hod.html` | HOD | Login → list users → update org unit → read fees/homework → failure scenarios |
| 4 | `20_staff.html` | Staff | Login → list users → own profile → read fees → failure scenarios |
| 5 | `21_cross_institution.html` | Cross-institution | Login → read client → list institutions → read org units → failure scenarios |

### Phase 2: Failure Scenario Enhancements (update existing files)
| # | File | Enhancement |
|---|---|---|
| 1 | `11_error_edge_cases.html` | Add profile failures, RLS failures, more cross-role failures |
| 2 | `07_tenant_isolation.html` | Add RLS failure scenarios |

### Phase 3: Index Update
| # | File | Enhancement |
|---|---|---|
| 1 | `index.html` | Add links to new flows 17-21 |

---

## Total New Steps Needed

| Flow | Happy Paths | Failure Scenarios | Total |
|---|---|---|---|
| 17_admin | 13 | 5 | 18 |
| 18_principal | 7 | 5 | 12 |
| 19_hod | 7 | 4 | 11 |
| 20_staff | 5 | 5 | 10 |
| 21_cross_institution | 6 | 6 | 12 |
| 11_error_edge_cases (update) | — | 8 | 8 |
| **Total** | **38** | **33** | **71** |
