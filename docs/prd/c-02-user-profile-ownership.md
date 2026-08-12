# PRD — C-02 UserProfile Self-Service & Ownership

> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Capability layer / phase:** Kernel · Critical · Phase 1
> **Status:** Draft for impact classification → sdd-stack
> **Last updated:** 2026-08-12
> **Decisional source of truth:** D13 (to be added to `docs/architecture/adr-c02-identity-user-management-implementation.md`)
> **Companion docs:** `docs/platform-capabilities/platform-capabilities-v3.md` §C-02, §C-04

---

## 1. Problem

Flow 16 testing revealed 5 issues with the UserProfile system:

| # | Problem | Impact |
|---|---|---|
| 1 | `UserProfile.user_id` FK → `app_user.id` | CD users (in `client_user`) can't have profiles — same FK pattern as D12 |
| 2 | No role has `user_profile.create` permission | `POST /api/v1/users/{id}/profile` returns 403 for everyone |
| 3 | No ownership check on profile endpoints | Any user with `user_profile.update` can update any other user's profile |
| 4 | Teacher/Staff/Student/Parent don't have `user_profile.update` | Users can't update their own profile |
| 5 | No ownership check on profile read | Any user with `user_profile.read` can see any profile |

---

## 2. Goals & Non-goals

### 2.1 In scope

| Concern | Notes |
|---|---|
| **Self-service profile management** | Any authenticated user can create/read/update their own profile without needing `user_profile.create` permission |
| **Admin profile management** | Admin/CD/institution_admin can create/read/update profiles on behalf of users using `user_profile.create` permission |
| **Ownership enforcement** | Profile endpoints pass `owner_id=user_id` to `check_permission`. Self-access passes; non-admin access to others' profiles is blocked |
| **Cross-tier FK fix** | `UserProfile.user_id` FK → `user_account.id` (D12 pattern) so CD users can have profiles |
| **Permission assignment** | `user_profile.create` for Admin/CD/institution_admin; `user_profile.update` and `user_profile.read` for ALL roles |

### 2.2 Out of scope

| Concern | Notes |
|---|---|
| Profile photo upload | File service — C-02 Phase 2 |
| Profile deletion | No endpoint exists |
| Bulk profile import | Future capability |

---

## 3. Users / Personas

| Persona | Can create own profile? | Can update own profile? | Can read own profile? | Can manage others' profiles? |
|---|---|---|---|---|
| Admin | ✅ | ✅ | ✅ | ✅ (any in institution) |
| client_director | ✅ | ✅ | ✅ | ✅ (any in tenant) |
| institution_admin | ✅ | ✅ | ✅ | ✅ (any in institution) |
| Teacher | ✅ | ✅ | ✅ | ❌ |
| Staff | ✅ | ✅ | ✅ | ❌ |
| Student | ✅ | ✅ | ✅ | ❌ |
| Parent | ✅ | ✅ | ✅ | ❌ |

---

## 4. User Journeys

### 4.1 Teacher updates own profile

1. Teacher logs in
2. Teacher calls `PATCH /api/v1/users/{teacher_id}/profile` with `{date_of_birth, gender, blood_group}`
3. Backend checks: `owner_id == ctx.user_id` → passes (self-access)
4. Profile updated → 200

### 4.2 CD creates profile for student

1. CD logs in
2. CD calls `POST /api/v1/users/{student_id}/profile` with `{date_of_birth, gender, blood_group}`
3. Backend checks: CD has `user_profile.create` with tenant scope → passes
4. Profile created → 201

### 4.3 Student creates own profile

1. Student logs in
2. Student calls `POST /api/v1/users/{student_id}/profile` with `{date_of_birth, gender, blood_group}`
3. Backend checks: `owner_id == ctx.user_id` → passes (self-creation without `user_profile.create`)
4. Profile created → 201

### 4.4 Teacher tries to update another teacher's profile

1. Teacher logs in
2. Teacher calls `PATCH /api/v1/users/{other_teacher_id}/profile`
3. Backend checks: `owner_id != ctx.user_id` → blocked (self-only, no institution bypass for non-admin)
4. 403 Forbidden

### 4.5 Admin updates any profile

1. Admin logs in
2. Admin calls `PATCH /api/v1/users/{any_user_id}/profile`
3. Backend checks: `owner_id != ctx.user_id` but Admin has institution scope → passes (admin bypass)
4. Profile updated → 200

---

## 5. Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC-1 | `UserProfile.user_id` FK references `user_account.id` |
| AC-2 | All roles have `user_profile.read` and `user_profile.update` permissions |
| AC-3 | Admin/CD/institution_admin have `user_profile.create` permission |
| AC-4 | `POST /api/v1/users/{id}/profile` allows self-creation without `user_profile.create` (owner_id check) |
| AC-5 | `PATCH /api/v1/users/{id}/profile` passes `owner_id=user_id` — self-only for non-admin |
| AC-6 | `GET /api/v1/users/{id}/profile` passes `owner_id=user_id` — self-only for non-admin |
| AC-7 | Admin can create/update any profile (institution scope bypass) |
| AC-8 | CD user (in `client_user`) can have a UserProfile (FK fix) |

---

## 6. Key Decisions

| # | Decision | Rationale |
|---|---|---|
| D13-a | Self-only ownership (no institution bypass for non-admin) | Profiles contain personal data (DOB, gender). Teachers shouldn't see other teachers' personal info. |
| D13-b | Self-creation without `user_profile.create` permission | Users should be able to set up their own profile without admin intervention. `user_profile.create` is for admin creating on behalf of others. |
| D13-c | `UserProfile.user_id` FK → `user_account.id` | Same pattern as D12. Enables CD users to have profiles. |

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Self-creation bypass could be exploited | `owner_id` check ensures only the authenticated user can create their own profile. Admin can create for others. |
| Migration backfill for existing profiles | Profiles already reference `app_user.id`. Backfill `user_account` rows for existing profile user_ids (same as D12). |
