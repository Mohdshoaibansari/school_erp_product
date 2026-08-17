# Frontend Gap Analysis — Missing Functionality by Role

> **Date:** 2026-08-15
> **Scope:** Backend APIs (`backend/`) vs Journey Docs (`user_journey/`) vs Current Frontend (`frontend/src/`)
> **Status:** Comprehensive audit of all 10 roles

---

## Executive Summary

| Role | Backend APIs | Journey Happy Paths | Frontend Screens | Gap Severity |
|---|---|---|---|---|
| **Platform Owner** | 12 endpoints | 8 paths | ✅ Full coverage | 🟢 Low |
| **Client Director** | 10 endpoints | 7 paths | ✅ Full coverage | 🟢 Low |
| **Institution Admin** | 25+ endpoints | 15 paths | ⚠️ Mostly covered | 🟡 Medium |
| **Admin** | 20+ endpoints | 13 paths | ⚠️ Partial (shares inst_admin) | 🟡 Medium |
| **Principal** | 12 endpoints | 7 paths | ❌ Minimal | 🔴 High |
| **HOD** | 8 endpoints | 7 paths | ❌ Minimal | 🔴 High |
| **Teacher** | 12 endpoints | 11 paths | ❌ No dedicated screens | 🔴 High |
| **Staff** | 5 endpoints | 5 paths | ❌ No screens | 🔴 High |
| **Student** | 8 endpoints | 10 paths | ❌ Placeholder only | 🔴 High |
| **Parent** | 3 endpoints | 4 paths | ❌ Placeholder only | 🔴 High |

---

## 1. Platform Owner 🟢

**Backend permissions:** `client.*`, `institution_type.*`, `institution.create/read`, `user.create/read`, `org_unit.read`, `config.*`

**Frontend coverage:** ✅ Complete
- ✅ Clients list + detail + create + transition
- ✅ Client Users (bootstrap director, list, transition, revoke)
- ✅ Institution Types (CRUD)
- ✅ Ownership Transfers (initiate, approve/reject)

**Minor gaps:**
- ❌ No UI for platform-level config keys (backend has `config.key.create` at tenant scope)
- ❌ No dashboard/overview screen showing system health metrics

---

## 2. Client Director 🟢

**Backend permissions:** `institution.*` (tenant scope), `user.*` (tenant scope), `org_unit.*` (tenant scope), `fee.*` (tenant scope), `homework.*` (tenant scope)

**Frontend coverage:** ✅ Complete
- ✅ Institutions list + create + transition + go-live
- ✅ Org Units (CRUD + tree view)
- ✅ Users list + detail + create + transition
- ✅ Role assignments

**Minor gaps:**
- ❌ No cross-institution dashboard (view all institutions at a glance)
- ❌ No bulk operations (bulk user import, bulk institution management)

---

## 3. Institution Admin 🟡

**Backend permissions:** `user.*`, `academic_year.*`, `teacher_assignment.*`, `enrollment.*`, `org_unit.*`, `fee.*`, `homework.*`, `submission.read`, `grade.*`, `config.value.*`, `user_profile.admin`

**Frontend coverage:** ⚠️ Mostly covered
- ✅ Users (CRUD + transition + role assignments)
- ✅ Academic Years (create + transition + structure view)
- ✅ Subjects + Subject Groups (CRUD)
- ✅ Teacher Assignments (CRUD — built but route says "coming soon")
- ✅ Enrollments (CRUD — built but route says "coming soon")
- ✅ Fee Types + Fee Assignments + Payments (CRUD)
- ✅ Homework + Submissions + Grades (CRUD)
- ✅ Config Keys + Config Audit
- ✅ Org Units

**Gaps:**
- ❌ **Teacher Assignments route** — Component exists (`TeacherAssignments.tsx`) but route shows "Coming Soon" placeholder (needs section/year context selection)
- ❌ **Enrollments route** — Component exists (`Enrollments.tsx`) but route shows "Coming Soon" placeholder (needs section context)
- ❌ **User Profile management** — Backend has `user_profile.admin` permission, but no UI to view/edit profiles for other users
- ❌ **User Identifiers** — Backend has `user_identifier.*` endpoints, no UI
- ❌ **Role Assignment management** — Backend has `role_assignment.*` endpoints, only basic role display in UserDetail
- ❌ **Config Values** — Backend has `config.value.*` endpoints, frontend only shows keys (not value overrides)
- ❌ **Go-Live workflow** — Backend has `/institutions/{id}/go-live` endpoint, no UI button/wizard
- ❌ **Academic Year transition** — Backend has year lifecycle transitions, no UI button
- ❌ **Homework close** — Backend has `POST /homeworks/{id}/close`, no UI action
- ❌ **Fee waiver** — Backend has `POST /fee-assignments/{id}/waive`, no UI action
- ❌ **Submission view** — Backend has full submission CRUD, frontend has list but limited detail view
- ❌ **Receipt generation** — Backend has `receipt.read` permission, no UI

---

## 4. Admin 🟡

**Backend permissions:** Same as Institution Admin (both get all institution-scoped permissions)

**Frontend coverage:** ⚠️ Partially covered via `institution_admin` role mapping
- ✅ Same screens as Institution Admin (role is mapped via `user_tier: "institution"`)
- ⚠️ The `Admin` role name (capitalized) is now normalized to `admin` in the frontend

**Gaps (same as Institution Admin, plus):**
- ❌ All gaps listed under Institution Admin
- ❌ **No dedicated Admin dashboard** — Admin has the same view as institution_admin but the journey doc expects admin-specific workflows (user creation wizard, fee management workflow)

---

## 5. Principal 🔴

**Backend permissions:** `user.read`, `academic_year.*`, `teacher_assignment.*`, `enrollment.*`, `org_unit.*`, `fee.read`, `fee_assignment.read`, `payment.read`, `homework.read`, `submission.read`, `grade.read`, `role_assignment.read`

**Frontend coverage:** ❌ Minimal
- ✅ Users list (read-only via nav config)
- ✅ Academic management (years, subjects, subject groups)
- ⚠️ Homework view (read-only, but UI shows create/edit buttons that will 403)

**Missing screens/functionality:**
- ❌ **Institution detail view** — Principal can read/update institution, no dedicated screen
- ❌ **Org Unit management** — Principal has `org_unit.*`, no accessible route (route exists but not in Principal's nav)
- ❌ **Enrollment management** — Principal has `enrollment.*`, no accessible route
- ❌ **Teacher Assignment management** — Principal has `teacher_assignment.*`, no accessible route
- ❌ **Fee read-only view** — Principal has `fee.read`, `fee_assignment.read`, `payment.read` but no route in nav
- ❌ **Submission/Grade read-only view** — Backend allows read, no dedicated view
- ❌ **Role Assignment read** — Backend allows read, no UI
- ❌ **Homework read-only** — UI currently shows CRUD buttons that would 403 for Principal

**Action buttons that will fail for Principal:**
- Create/Edit/Delete buttons on Users page (Principal has `user.read` only)
- Create/Edit/Delete buttons on Homework page (Principal has `homework.read` only)
- Create/Edit buttons on Fee pages (Principal has `fee.read` only)

---

## 6. HOD (Head of Department) 🔴

**Backend permissions:** `user.read`, `academic_year.read`, `teacher_assignment.read`, `enrollment.read`, `org_unit.update`, `fee_assignment.read`, `payment.read`, `homework.read`, `submission.read`, `grade.read`

**Frontend coverage:** ❌ Minimal
- ✅ Subjects (via nav config, but read-only)
- ✅ Homework (via nav config, but read-only)

**Missing screens/functionality:**
- ❌ **Users list (read-only)** — HOD has `user.read`, no route in nav
- ❌ **Org Unit update** — HOD has `org_unit.update`, no route in nav
- ❌ **Fee Assignment read-only view** — HOD has `fee_assignment.read`, `payment.read`
- ❌ **Submission read-only view** — HOD has `submission.read`
- ❌ **Grade read-only view** — HOD has `grade.read`
- ❌ **Enrollment read-only view** — HOD has `enrollment.read`
- ❌ **Teacher Assignment read-only view** — HOD has `teacher_assignment.read`

**Action buttons that will fail for HOD:**
- All CRUD buttons on pages HOD can access (read-only permissions only)

---

## 7. Teacher 🔴

**Backend permissions:** `user.read/update` (own only), `academic_year.read`, `teacher_assignment.read`, `enrollment.read`, `homework.*`, `submission.read`, `grade.*`, `fee_assignment.read`, `user_profile.create/read` (own)

**Frontend coverage:** ❌ No dedicated screens
- ✅ Homework (via nav config — create, edit, delete, close)
- ✅ Grades (via nav config — create, update)
- ⚠️ Homework route includes teacher, but Submissions route does not

**Missing screens/functionality:**
- ❌ **Submission review** — Teacher has `submission.read`, Submissions component exists but not in teacher's nav
- ❌ **My Students view** — No way for teacher to see their assigned students
- ❌ **My Classes view** — No dashboard showing teacher's assigned subjects/sections
- ❌ **My Profile** — Teacher has `user_profile.create/read` for own profile, no dedicated screen
- ❌ **Fee Assignment read-only** — Teacher has `fee_assignment.read`, no view
- ❌ **Enrollment read-only** — Teacher has `enrollment.read`, no view
- ❌ **Teacher Assignment read-only** — Teacher has `teacher_assignment.read`, no view to see own assignments

**Action buttons that will fail for Teacher:**
- User management buttons (Teacher has `user.read/update` only, no create/delete)
- Any admin-level buttons that might appear

---

## 8. Staff 🔴

**Backend permissions:** `user.read/update` (own only), `academic_year.read`, `teacher_assignment.read`, `enrollment.read`, `fee_assignment.read`, `user_profile.create/read` (own)

**Frontend coverage:** ❌ No screens at all

**Missing screens/functionality:**
- ❌ **Users list (read-only)** — Staff has `user.read`, no route
- ❌ **My Profile** — Staff has `user_profile.create/read`, no screen
- ❌ **Fee Assignment read-only** — Staff has `fee_assignment.read`, no view
- ❌ **Enrollment read-only** — Staff has `enrollment.read`, no view
- ❌ **No nav items** — Staff role is not in any nav item's role list

---

## 9. Student 🔴

**Backend permissions:** `user.read` (own only), `academic_year.read`, `teacher_assignment.read`, `enrollment.read`, `homework.read`, `submission.*` (own), `grade.read` (own), `fee_assignment.read`, `payment.read`, `user_profile.create/read` (own)

**Frontend coverage:** ❌ Placeholder only
- ✅ Routes created: `/student/homework`, `/student/grades` (Coming Soon placeholders)

**Missing screens/functionality:**
- ❌ **My Homework** — Student has `homework.read`, needs list of assigned homework with due dates
- ❌ **Submit Homework** — Student has `submission.create`, needs submission form
- ❌ **My Submissions** — Student has `submission.read`, needs submission history
- ❌ **My Grades** — Student has `grade.read`, needs grade view with feedback
- ❌ **My Fee Status** — Student has `fee_assignment.read`, `payment.read`, needs fee dashboard
- ❌ **My Profile** — Student has `user_profile.create/read`, needs profile view/edit
- ❌ **My Enrollments** — Student has `enrollment.read`, needs enrollment info

**Backend APIs that exist but have no frontend:**
- `GET /homeworks` — list homework (student can read)
- `POST /submissions` — submit homework
- `GET /submissions` — view own submissions
- `GET /submissions/{id}` — view graded submission with feedback
- `GET /fee-assignments` — view fee assignments
- `GET /payments` — view payment history
- `GET /users/{id}/profile` — view own profile
- `PATCH /users/{id}/profile` — update own profile

---

## 10. Parent 🔴

**Backend permissions:** `user.read` (own only), `user_profile.create/read` (own)

**Frontend coverage:** ❌ Placeholder only
- ✅ Route created: `/parent/progress` (Coming Soon placeholder)

**Missing screens/functionality:**
- ❌ **My Profile** — Parent has `user_profile.create/read`, no screen
- ❌ **Child Progress** — No `parent_child_relationship` entity exists in backend yet (noted in journey doc as future)
- ❌ **No nav items beyond placeholder**

**Note:** Parent is explicitly a **placeholder role** per the journey docs. The `parent_child_relationship` entity doesn't exist yet. When it does, Parent will need:
- Child's homework list
- Child's grades
- Child's fee status
- Child's attendance (future)

---

## 11. Cross-Cutting Gaps

### A. Conditional Action Visibility
**Problem:** All CRUD screens show create/edit/delete buttons regardless of the user's permissions. Read-only roles (Principal, HOD, Teacher, Staff, Student) see buttons that will trigger 403 errors from the backend.

**Affected screens:** Users, Homework, Fees, Academic, Config

**Fix needed:** Either:
1. **Permission-aware buttons** — hide/disable buttons based on the user's backend permissions (requires the JWT to include permission names, or a permissions API)
2. **Role-aware buttons** — hide/disable buttons based on role (simpler but less granular)

### B. User Profile Management
**Problem:** Backend has full `user_profile.*` and `user_identifier.*` APIs, but no UI exists for any role to manage profiles.

**Backend endpoints:**
- `POST /users/{id}/profile` — create profile
- `GET /users/{id}/profile` — read profile
- `PATCH /users/{id}/profile` — update profile
- `POST /users/{id}/identifiers` — create identifier
- `GET /users/{id}/identifiers` — list identifiers
- `DELETE /users/{id}/identifiers/{id}` — delete identifier

**Needed for:** All roles (own profile), Admin/InstAdmin (any profile)

### C. Role Assignment UI
**Problem:** Backend has `role_assignment.*` endpoints but UI only shows roles as a read-only list in UserDetail.

**Backend endpoints:**
- `POST /users/{user_id}/roles` — assign role
- `GET /users/{user_id}/roles` — list assignments
- `DELETE /users/{user_id}/roles/{id}` — remove assignment

**Needed for:** Admin, Institution Admin, Principal (read)

### D. Config Value Overrides
**Problem:** Frontend shows config keys but not the actual resolved values or per-institution overrides.

**Backend endpoints:**
- `GET /config/values` — list values
- `POST /config/values` — create value override
- `PATCH /config/values/{id}` — update value
- `DELETE /config/values/{id}` — delete value
- `POST /config/resolve` — resolve effective value

**Needed for:** Admin, Institution Admin

### E. Academic Context Selection
**Problem:** TeacherAssignments and Enrollments components require `sectionId` and `academicYearId` props, but no route-level context selection exists. These screens show "Coming Soon" in the router.

**Fix needed:** A context picker (academic year → section) that wraps these components, or URL-param-driven routes.

### F. Friendly 403 Handling
**Problem:** When a read-only role triggers a write action (e.g., Principal clicking "Create User"), the backend returns 403. The frontend shows a generic error toast instead of a friendly "You don't have permission for this action" message.

**Fix needed:** Axios interceptor that detects 403 and shows a permission-specific toast/modal.

---

## 12. Priority Matrix

### P0 — Critical (blocks role functionality)
| # | Gap | Affected Roles | Effort |
|---|---|---|---|
| 1 | Student homework submission + grades screens | Student | 3-5 days |
| 2 | Teacher submission review + grading screens | Teacher | 2-3 days |
| 3 | Conditional action visibility (hide write buttons for read-only roles) | Principal, HOD, Teacher, Staff, Student | 2-3 days |
| 4 | Add missing nav items for Principal, HOD, Staff | Principal, HOD, Staff | 1 day |

### P1 — High (significant UX improvement)
| # | Gap | Affected Roles | Effort |
|---|---|---|---|
| 5 | User Profile view/edit screen | All roles | 2-3 days |
| 6 | Student fee dashboard (read-only) | Student | 1-2 days |
| 7 | Teacher "My Classes" dashboard | Teacher | 2-3 days |
| 8 | Academic context selection (year → section picker) | Admin, InstAdmin | 1-2 days |
| 9 | Role Assignment management UI | Admin, InstAdmin | 1-2 days |
| 10 | Config value override UI | Admin, InstAdmin | 1-2 days |

### P2 — Medium (completeness)
| # | Gap | Affected Roles | Effort |
|---|---|---|---|
| 11 | Parent profile screen | Parent | 0.5 day |
| 12 | Staff profile screen | Staff | 0.5 day |
| 13 | Fee waiver UI action | Admin, InstAdmin | 0.5 day |
| 14 | Homework close UI action | Teacher, Admin | 0.5 day |
| 15 | Go-Live workflow wizard | Client Director | 1 day |
| 16 | Academic year transition UI | Admin, InstAdmin | 0.5 day |
| 17 | Receipt generation UI | Admin, InstAdmin | 1 day |
| 18 | Friendly 403 interceptor | All read-only roles | 1 day |

### P3 — Low (future)
| # | Gap | Affected Roles | Effort |
|---|---|---|---|
| 19 | Parent child progress (blocked by backend) | Parent | Blocked |
| 20 | Cross-institution dashboard | Client Director | 2-3 days |
| 21 | Bulk user import | Admin, InstAdmin | 3-5 days |
| 22 | User identifier management | Admin, InstAdmin | 1 day |
| 23 | Platform config management UI | Platform Owner | 1-2 days |

---

## 13. Backend Permission → Frontend Nav Mapping (Current State)

| Nav Item | Required Roles | Backend Permission |
|---|---|---|
| Clients | platform_owner | `client.*` |
| Institution Types | platform_owner | `institution_type.*` |
| Ownership Transfers | platform_owner | `client.transition_lifecycle` |
| Institutions | client_director | `institution.*` (tenant) |
| Users | client_director, institution_admin, admin, principal | `user.*` |
| Academic Years | institution_admin, admin, principal | `academic_year.*` |
| Structure | institution_admin, admin, principal | `academic_year.read` |
| Subjects | institution_admin, admin, principal, hod | `academic_year.read` |
| Subject Groups | institution_admin, admin, principal | `academic_year.read` |
| Teacher Assignments | institution_admin, admin, principal | `teacher_assignment.*` |
| Enrollments | institution_admin, admin, principal | `enrollment.*` |
| Config Keys | institution_admin, admin | `config.key.*` |
| Config Audit | institution_admin, admin | `config.audit.read` |
| Fee Types | institution_admin, admin | `fee.*` |
| Fee Assignments | institution_admin, admin | `fee_assignment.*` |
| Payments | institution_admin, admin | `payment.*` |
| Homework | institution_admin, admin, teacher, hod | `homework.*` |
| Grades | institution_admin, admin, teacher, hod | `grade.*` |
| My Homework | student | `homework.read` |
| My Grades | student | `grade.read` |
| Child Progress | parent | (blocked — no backend entity) |

**Roles with NO nav items:** staff ❌

---

## 14. Recommended Implementation Order

### Sprint 1: Read-Only Role Support (3-4 days)
1. Add nav items for Principal, HOD, Staff (read-only views)
2. Implement conditional action visibility (hide write buttons for read-only roles)
3. Add friendly 403 interceptor
4. Wire up TeacherAssignments and Enrollments routes with context selection

### Sprint 2: Student Experience (3-5 days)
5. Build Student Homework screen (list assigned homework)
6. Build Homework Submission form
7. Build Student Grades screen (view graded submissions)
8. Build Student Fee Dashboard (read-only)
9. Build Student Profile view/edit

### Sprint 3: Teacher Experience (2-3 days)
10. Build Teacher "My Classes" dashboard
11. Build Submission Review screen (teacher views + grades)
12. Wire up existing Homework + Grades screens for teacher workflow
13. Build Teacher Profile view/edit

### Sprint 4: Admin Completeness (2-3 days)
14. Build User Profile management screen
15. Build Role Assignment management UI
16. Build Config Values screen
17. Add fee waiver, homework close, go-live actions
18. Wire up remaining CRUD actions

### Sprint 5: Polish (1-2 days)
19. Staff + Parent profile screens
20. Cross-institution dashboard
21. Bulk operations
22. Receipt generation
