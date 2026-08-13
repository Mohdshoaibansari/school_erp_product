# PRD — C-02 UserProfile Self-Service & Admin Management

> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Capability layer / phase:** Kernel · Critical · Phase 1
> **Status:** Draft for sdd-stack
> **Last updated:** 2026-08-13
> **Decisional source of truth:** D13 (ADR)

---

## 1. Problem

| # | Problem | Impact |
|---|---|---|
| 1 | `UserProfile.user_id` FK → `app_user.id` | CD users (in `client_user`) can't have profiles |
| 2 | No role has `user_profile.create` permission | `POST /api/v1/users/{id}/profile` returns 403 for everyone |
| 3 | No clean admin vs self-service separation | Need a way for admins to manage any profile while restricting non-admins to their own |
| 4 | Teacher/Staff/Student/Parent can't manage own profile | Missing `user_profile.update` and `user_profile.read` permissions |
| 5 | Stage 5 ownership check in `_check_impl` is broken | Uses empty `client_id`/`institution_id` — can't distinguish admin from non-admin roles |

---

## 2. Goals & Non-goals

### 2.1 In scope

| Concern | Notes |
|---|---|
| **Self-service profile management** | Any authenticated user can create/read/update their own profile via `owner_id` check (Stage 3 bypass) |
| **Admin profile management** | Admin/CD/institution_admin can manage any profile via new `user_profile.admin` permission (Casbin check) |
| **Simplified authorization** | Remove ownership check (Stage 5) from `_check_impl`. Self-access (Stage 3) + Casbin (Stage 4) handle all cases |
| **Cross-tier FK fix** | `UserProfile.user_id` FK → `user_account.id` (D12 pattern) so CD users can have profiles |

### 2.2 Out of scope

| Concern | Notes |
|---|---|
| Profile photo upload | File service — C-02 Phase 2 |
| Profile deletion | No endpoint exists |
| Bulk profile import | Future capability |

---

## 3. Users / Personas

| Persona | Can manage own profile? | Can manage others' profiles? | Via |
|---|---|---|---|
| Admin | ✅ (Stage 3 bypass) | ✅ (`user_profile.admin` + institution scope) | Casbin |
| client_director | ✅ (Stage 3 bypass) | ✅ (`user_profile.admin` + tenant scope) | Casbin |
| institution_admin | ✅ (Stage 3 bypass) | ✅ (`user_profile.admin` + institution scope) | Casbin |
| Teacher | ✅ (Stage 3 bypass) | ❌ (no `user_profile.admin`) | — |
| Staff | ✅ (Stage 3 bypass) | ❌ (no `user_profile.admin`) | — |
| Student | ✅ (Stage 3 bypass) | ❌ (no `user_profile.admin`) | — |
| Parent | ✅ (Stage 3 bypass) | ❌ (no `user_profile.admin`) | — |

---

## 4. User Journeys

### 4.1 Teacher updates own profile
1. Teacher logs in
2. Teacher calls `PATCH /api/v1/users/{teacher_id}/profile` with `{date_of_birth, gender, blood_group}`
3. Backend: Stage 3 (`owner_id == ctx.user_id`) → self-access bypass → return
4. Profile updated → 200

### 4.2 CD creates profile for student
1. CD logs in
2. CD calls `POST /api/v1/users/{student_id}/profile`
3. Backend: Stage 3 (`owner_id ≠ ctx.user_id`) → not self → Stage 4: Casbin checks `user_profile.admin` at tenant scope → ✅ passes
4. Profile created → 201

### 4.3 Student creates own profile
1. Student logs in
2. Student calls `POST /api/v1/users/{student_id}/profile`
3. Backend: Stage 3 (`owner_id == ctx.user_id`) → self-access bypass → return
4. Profile created → 201

### 4.4 Teacher tries to update another teacher's profile
1. Teacher logs in
2. Teacher calls `PATCH /api/v1/users/{other_teacher_id}/profile`
3. Backend: Stage 3 (`owner_id ≠ ctx.user_id`) → not self → Stage 4: Casbin checks `user_profile.admin` → ❌ Teacher has no `user_profile.admin`
4. 403 Forbidden

### 4.5 Admin updates any profile
1. Admin logs in
2. Admin calls `PATCH /api/v1/users/{any_user_id}/profile`
3. Backend: Stage 3 (`owner_id ≠ ctx.user_id`) → not self → Stage 4: Casbin checks `user_profile.admin` at institution scope → ✅ passes
4. Profile updated → 200

---

## 5. Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC-1 | `UserProfile.user_id` FK references `user_account.id` |
| AC-2 | `user_profile.admin` permission exists and is assigned to Admin/CD/institution_admin |
| AC-3 | All roles can manage own profile (Stage 3 self-access bypass) |
| AC-4 | Admin/CD/institution_admin can manage any profile (Casbin `user_profile.admin` check) |
| AC-5 | Teacher CANNOT manage another teacher's profile (no `user_profile.admin`) |
| AC-6 | Stage 5 (ownership check) removed from `_check_impl` |
| AC-7 | CD user (in `client_user`) can have a UserProfile (FK fix) |

---

## 6. Key Decisions

| # | Decision | Rationale |
|---|---|---|
| D13-a | Two-tier permission model: self-service (Stage 3) + admin (`user_profile.admin`) | Clean separation. No complex ownership bypass logic. |
| D13-b | Remove Stage 5 (ownership check) from `_check_impl` | Casbin + self-access handle all cases. Eliminates broken admin bypass. |
| D13-c | `UserProfile.user_id` FK → `user_account.id` | Same pattern as D12. Enables CD users to have profiles. |

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Self-service bypass could be exploited | `owner_id` check ensures only the authenticated user can access their own profile |
| Migration backfill for existing profiles | Profiles already reference `app_user.id`. Backfill `user_account` rows (same as D12) |
| Removing Stage 5 affects other resources | Stage 5 only runs when `owner_id` is set. Only profile routes pass `owner_id`. Other resources unaffected |
