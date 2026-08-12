# Tasks — fix-user-profile-ownership

> **Change ID:** fix-user-profile-ownership
> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Status:** Tasks
> **Created:** 2026-08-12
> **Design source:** `openspec/changes/fix-user-profile-ownership/design.md`

---

## Task List

### T1: Migration 018 — UserProfile FK Change

**Description:** Create Alembic migration to change `user_profile.user_id` FK from `app_user.id` to `user_account.id`. Include backfill step to ensure all existing profile user_ids have corresponding `user_account` rows.

**Acceptance Criteria:**
- AC-1: `UserProfile.user_id` FK references `user_account.id`
- AC-8: CD user (in `client_user`) can have a UserProfile

**Implementation Steps:**
1. Create `backend/migrations/versions/018_fix_user_profile_fk.py`
2. Implement backfill: `INSERT INTO user_account (id) SELECT DISTINCT up.user_id FROM user_profile up WHERE NOT EXISTS (SELECT 1 FROM user_account ua WHERE ua.id = up.user_id) ON CONFLICT (id) DO NOTHING`
3. Drop existing FK constraint: `op.drop_constraint("user_profile_user_id_fkey", "user_profile", type_="foreignkey")`
4. Create new FK: `op.create_foreign_key("user_profile_user_id_fkey", "user_profile", "user_account", ["user_id"], ["id"])`
5. Implement downgrade to reverse FK back to `app_user.id`

**Test:** MT-1 (migration applies cleanly), MT-2 (backfill completes)

**Files:** `backend/migrations/versions/018_fix_user_profile_fk.py` (new)

---

### T2: Model Update — UserProfile FK Target

**Description:** Update the SQLAlchemy model to reflect the new FK target.

**Acceptance Criteria:**
- AC-1: `UserProfile.user_id` FK references `user_account.id`

**Implementation Steps:**
1. Open `backend/kernel/user/models/user_profile.py`
2. Change line 22: `ForeignKey("app_user.id")` → `ForeignKey("user_account.id")`
3. Keep the `user` relationship pointing to `User` (app_user) for backward compatibility

**Files:** `backend/kernel/user/models/user_profile.py`

---

### T3: Migration 019 — Role-Permission Seed Data

**Description:** Create Alembic migration to insert `user_profile.create` permission and update role-permission mappings for all roles.

**Acceptance Criteria:**
- AC-2: All roles have `user_profile.read` and `user_profile.update` permissions
- AC-3: Admin/CD/institution_admin have `user_profile.create` permission

**Implementation Steps:**
1. Create `backend/migrations/versions/019_user_profile_permissions.py`
2. Insert permission: `INSERT INTO permission (name, resource, action) VALUES ('user_profile.create', 'user_profile', 'create') ON CONFLICT (name) DO NOTHING`
3. Define admin permissions: `["user_profile.create", "user_profile.read", "user_profile.update"]`
4. Define basic permissions: `["user_profile.read", "user_profile.update"]`
5. For each role, insert role_permission mappings with appropriate scope (institution/tenant)
6. Use `ON CONFLICT (role_id, permission_id) DO NOTHING` for idempotency

**Test:** MT-3 (permission exists), MT-4 (role mappings correct), MT-5 (idempotent)

**Files:** `backend/migrations/versions/019_user_profile_permissions.py` (new)

---

### T4: Code — Update `_check_impl` Ownership Logic

**Description:** Reorder `_check_impl` in `authz/dependencies.py` to check ownership before Casbin. This enables self-access without requiring `user_profile.create` permission.

**Acceptance Criteria:**
- AC-4: Self-creation without `user_profile.create` (owner_id check)
- AC-5: PATCH passes `owner_id=user_id` — self-only for non-admin
- AC-6: GET passes `owner_id=user_id` — self-only for non-admin
- AC-7: Admin can create/update any profile (institution scope bypass)

**Implementation Steps:**
1. Open `backend/kernel/authz/dependencies.py`
2. Locate `_check_impl` function
3. Reorder logic:
   - Platform owner bypass (unchanged)
   - Role validation (unchanged)
   - **NEW:** Ownership check — if `owner_id is not None and ctx.user_id and str(ctx.user_id) == str(owner_id)`, return immediately
   - Casbin check (unchanged, runs for non-self access)
4. Ensure `owner_id=None` (default) preserves existing behavior for all other callers

**Test:** T-1 through T-11 (all ownership scenarios)

**Files:** `backend/kernel/authz/dependencies.py`

---

### T5: Code — Update `create_profile` Route

**Description:** Add `owner_id=user_id` to the `POST /api/v1/users/{id}/profile` endpoint.

**Acceptance Criteria:**
- AC-4: Self-creation without `user_profile.create` (owner_id check)
- AC-7: Admin can create any profile (institution scope bypass)

**Implementation Steps:**
1. Open `backend/kernel/user/routes/profiles.py`
2. Locate `create_profile` function
3. Change: `Depends(require_permission("user_profile", "create"))` → `Depends(require_permission("user_profile", "create", owner_id=user_id))`

**Test:** T-1 (Teacher creates own), T-6 (Teacher blocked creating other's), T-9 (Admin creates any), T-10 (Duplicate 409)

**Files:** `backend/kernel/user/routes/profiles.py`

---

### T6: Code — Update `get_profile` Route

**Description:** Add `owner_id=user_id` to the `GET /api/v1/users/{id}/profile` endpoint.

**Acceptance Criteria:**
- AC-6: GET passes `owner_id=user_id` — self-only for non-admin
- AC-7: Admin can read any profile (institution scope bypass)

**Implementation Steps:**
1. Open `backend/kernel/user/routes/profiles.py`
2. Locate `get_profile` function
3. Change: `check_permission(ctx, enforcer, "user_profile", "read", ...)` → `check_permission(ctx, enforcer, "user_profile", "read", owner_id=user_id)`
4. Remove `obj_client_id` and `obj_institution_id` parameters (ownership check is primary gate)

**Test:** T-2 (Teacher reads own), T-4 (Teacher blocked reading other's), T-7 (Admin reads any)

**Files:** `backend/kernel/user/routes/profiles.py`

---

### T7: Code — Update `update_profile` Route

**Description:** Add `owner_id=user_id` to the `PATCH /api/v1/users/{id}/profile` endpoint.

**Acceptance Criteria:**
- AC-5: PATCH passes `owner_id=user_id` — self-only for non-admin
- AC-7: Admin can update any profile (institution scope bypass)

**Implementation Steps:**
1. Open `backend/kernel/user/routes/profiles.py`
2. Locate `update_profile` function
3. Change: `check_permission(ctx, enforcer, "user_profile", "update", ...)` → `check_permission(ctx, enforcer, "user_profile", "update", owner_id=user_id)`
4. Remove `obj_client_id` and `obj_institution_id` parameters (ownership check is primary gate)

**Test:** T-3 (Teacher updates own), T-5 (Teacher blocked updating other's), T-8 (Admin updates any)

**Files:** `backend/kernel/user/routes/profiles.py`

---

### T8: Tests — Ownership Test Cases

**Description:** Add comprehensive test scenarios to verify ownership enforcement and self-creation logic.

**Acceptance Criteria:**
- All AC-1 through AC-8 verified by tests

**Implementation Steps:**
1. Open `backend/tests/test_c02_user.py`
2. Add test class `TestUserProfileOwnership`
3. Implement test scenarios:
   - T-1: Teacher creates own profile (POST with owner_id == ctx.user_id) → 201
   - T-2: Teacher reads own profile (GET with owner_id == ctx.user_id) → 200
   - T-3: Teacher updates own profile (PATCH with owner_id == ctx.user_id) → 200
   - T-4: Teacher reads another teacher's profile (owner_id != ctx.user_id) → 403
   - T-5: Teacher updates another teacher's profile → 403
   - T-6: Teacher creates profile for another user → 403
   - T-7: Admin reads any profile (institution scope bypass) → 200
   - T-8: Admin updates any profile → 200
   - T-9: Admin creates profile for any user → 201
   - T-10: Duplicate profile creation (POST when profile exists) → 409
   - T-11: CD user has a UserProfile (FK fix) → 201
4. Add migration tests:
   - MT-1: Migration 018 applies cleanly
   - MT-2: Migration 018 backfills user_account for existing profiles
   - MT-3: Migration 019 inserts user_profile.create permission
   - MT-4: Migration 019 maps permissions to all roles
   - MT-5: Migration 019 is idempotent (run twice)

**Test:** Run full test suite to verify no regressions

**Files:** `backend/tests/test_c02_user.py`

---

## Implementation Order

| Order | Task | Dependencies |
|-------|------|--------------|
| 1 | T1: Migration 018 — FK change | None |
| 2 | T2: Model update | T1 |
| 3 | T3: Migration 019 — permissions | T1 |
| 4 | T4: Code — `_check_impl` reorder | T1 |
| 5 | T5: Code — `create_profile` route | T3, T4 |
| 6 | T6: Code — `get_profile` route | T3, T4 |
| 7 | T7: Code — `update_profile` route | T3, T4 |
| 8 | T8: Tests | T1, T2, T3, T4, T5, T6, T7 |

---

## Acceptance Criteria Traceability

| AC | Tasks |
|----|-------|
| AC-1 | T1, T2 |
| AC-2 | T3 |
| AC-3 | T3 |
| AC-4 | T4, T5 |
| AC-5 | T4, T7 |
| AC-6 | T4, T6 |
| AC-7 | T4, T5, T6, T7 |
| AC-8 | T1, T2 |
