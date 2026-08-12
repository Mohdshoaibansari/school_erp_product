# Verify — fix-user-profile-ownership

> **Change ID:** fix-user-profile-ownership
> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Status:** Verification
> **Created:** 2026-08-12
> **Verified against:** Current `main` branch state

---

## 1. Spec-to-Task Mapping

### Identity-User-Management Spec

| Requirement | Task(s) | Status | Evidence |
|-------------|---------|--------|----------|
| **UserProfile FK to user_account** | T1 (Migration 018), T2 (Model update) | ❌ NOT IMPLEMENTED | `user_profile.py:22` still has `ForeignKey("app_user.id")`. No migration 018 file exists. |
| **Ownership Enforcement on Profile Endpoints** | T4 (`_check_impl` reorder), T5-T7 (Route changes) | ❌ NOT IMPLEMENTED | Routes don't pass `owner_id=user_id`. `get_profile` and `update_profile` use `obj_client_id/obj_institution_id` instead. |
| **Self-Creation Without user_profile.create Permission** | T4 (`_check_impl` reorder), T5 (create_profile route) | ❌ NOT IMPLEMENTED | `_check_impl` runs Casbin FIRST (line ~60 in dependencies.py). Ownership check is AFTER Casbin (Step 2). Self-creation fails at Casbin step for users without `user_profile.create`. |
| **Profile Endpoint Authorization** | T5-T7 (Route changes) | ❌ NOT IMPLEMENTED | All three endpoints lack `owner_id` parameter. |

### Authorization Spec

| Requirement | Task(s) | Status | Evidence |
|-------------|---------|--------|----------|
| **Permission Catalog Update** | T3 (Migration 019) | ⚠️ PARTIALLY DONE | `user_profile.create` permission exists (inserted in migration 016, line 36). But migration 019 doesn't exist for role-permission mappings. |
| **Role-Permission Mapping for UserProfile** | T3 (Migration 019) | ❌ NOT IMPLEMENTED | Migration 016 only maps `user_profile.read/update` to `client_director`. Missing: Admin, institution_admin, Teacher, Staff, Student, Parent mappings. No migration 019 exists. |
| **Ownership Check Integration** | T4 (`_check_impl` reorder) | ⚠️ PARTIALLY DONE | `owner_id` parameter exists in `_check_impl` but ordering is wrong: Casbin runs FIRST, ownership AFTER. Design requires ownership BEFORE Casbin for self-access shortcut. |
| **Migration for Role-Permission Seed Data** | T3 (Migration 019) | ❌ NOT IMPLEMENTED | No migration 019 file exists in `backend/migrations/versions/`. |

---

## 2. Detailed Implementation Analysis

### 2.1 Model — `backend/kernel/user/models/user_profile.py`

**Current state (line 22):**
```python
user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), unique=True, nullable=False)
```

**Required state:**
```python
user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id"), unique=True, nullable=False)
```

**Impact:** CD users (in `client_user`) cannot have UserProfile records. FK constraint prevents insertion.

---

### 2.2 `_check_impl` — `backend/kernel/authz/dependencies.py`

**Current flow (lines 50-80):**
```
1. Platform owner bypass
2. Role validation
3. Casbin check ← FAILS here for users without permission
4. Ownership check (Step 2) ← NEVER REACHED for self-creation
```

**Design-required flow:**
```
1. Platform owner bypass
2. Role validation
3. Ownership check (self-access) ← PASSES here for self-creation
4. Casbin check (for non-self access)
```

**Impact:** A Teacher calling `POST /api/v1/users/{own_id}/profile` fails at step 3 because Teacher has no `user_profile.create` permission in Casbin. The ownership check at step 4 is never reached.

---

### 2.3 Routes — `backend/kernel/user/routes/profiles.py`

| Endpoint | Current Auth Check | Required Auth Check |
|----------|-------------------|---------------------|
| `POST /api/v1/users/{id}/profile` | `require_permission("user_profile", "create")` | `require_permission("user_profile", "create", owner_id=user_id)` |
| `GET /api/v1/users/{id}/profile` | `check_permission(ctx, enforcer, "user_profile", "read", obj_client_id=..., obj_institution_id=...)` | `check_permission(ctx, enforcer, "user_profile", "read", owner_id=user_id)` |
| `PATCH /api/v1/users/{id}/profile` | `check_permission(ctx, enforcer, "user_profile", "update", obj_client_id=..., obj_institution_id=...)` | `check_permission(ctx, enforcer, "user_profile", "update", owner_id=user_id)` |

---

### 2.4 Migrations

| Migration | Status | Evidence |
|-----------|--------|----------|
| `018_fix_user_profile_fk.py` | ❌ DOES NOT EXIST | Not found in `backend/migrations/versions/` |
| `019_user_profile_permissions.py` | ❌ DOES NOT EXIST | Not found in `backend/migrations/versions/` |

---

### 2.5 Tests

| Test Category | Status | Evidence |
|---------------|--------|----------|
| Ownership tests (T-1 to T-11) | ❌ NOT ADDED | No ownership test class in `test_c02_user.py` |
| Migration tests (MT-1 to MT-5) | ❌ NOT ADDED | No migration test scenarios |
| Self-creation tests | ❌ NOT ADDED | No self-creation test scenarios |

---

### 2.6 Current Role-Permission Mappings (Migration 016)

| Role | `user_profile.create` | `user_profile.read` | `user_profile.update` | Spec Required |
|------|----------------------|--------------------|-----------------------|---------------|
| Admin | ❌ (perm exists, not mapped) | ❌ (not mapped) | ❌ (not mapped) | ✅ All three |
| client_director | ❌ | ✅ (tenant) | ✅ (tenant) | ✅ All three |
| institution_admin | ❌ | ❌ | ❌ | ✅ All three |
| Teacher | ❌ | ❌ | ❌ | read + update |
| Staff | ❌ | ❌ | ❌ | read + update |
| Student | ❌ | ❌ | ❌ | read + update |
| Parent | ❌ | ❌ | ❌ | read + update |

---

## 3. Gap Summary

### Critical Gaps (Blocking)

1. **FK not changed**: UserProfile still references `app_user.id`, blocking CD users from having profiles (AC-1, AC-8)
2. **Ownership check ordering wrong**: Casbin-first blocks self-creation for non-admin users (AC-4, AC-5, AC-6)
3. **Routes missing `owner_id`**: All three endpoints lack ownership context (AC-4, AC-5, AC-6)

### High Gaps

4. **Missing role-permission mappings**: Admin, institution_admin, Teacher, Staff, Student, Parent lack required permissions (AC-2, AC-3)
5. **Missing migrations**: Both migration 018 and 019 don't exist

### Medium Gaps

6. **No tests**: Zero ownership/self-creation test coverage (T-1 to T-11, MT-1 to MT-5)

---

## 4. Post-Implementation Checklist

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | `UserProfile.user_id` FK references `user_account.id` | ❌ | Model not updated, migration not created |
| 2 | All roles have `user_profile.read` and `user_profile.update` | ❌ | Migration 019 not created |
| 3 | Admin/CD/institution_admin have `user_profile.create` | ❌ | Migration 019 not created |
| 4 | `POST` allows self-creation without `user_profile.create` | ❌ | `_check_impl` ordering wrong |
| 5 | `PATCH` passes `owner_id=user_id` | ❌ | Route not updated |
| 6 | `GET` passes `owner_id=user_id` | ❌ | Route not updated |
| 7 | Admin can create/update any profile (institution scope) | ⚠️ | Works if permissions mapped correctly |
| 8 | CD user can have UserProfile (FK fix) | ❌ | FK not changed |
| 9 | Migration 018 applies cleanly | N/A | Migration doesn't exist |
| 10 | Migration 018 backfills user_account | N/A | Migration doesn't exist |
| 11 | Migration 019 inserts `user_profile.create` | N/A | Migration doesn't exist |
| 12 | Migration 019 maps permissions to all roles | N/A | Migration doesn't exist |
| 13 | Migration 019 is idempotent | N/A | Migration doesn't exist |
| 14 | Ownership tests pass (T-1 to T-11) | ❌ | Tests not created |
| 15 | Migration tests pass (MT-1 to MT-5) | ❌ | Tests not created |
| 16 | Existing test suite passes (no regressions) | ⚠️ | Cannot verify without running tests |
| 17 | No staged files outside change scope | ✅ | Git status shows only openspec artifacts |

---

## 5. Implementation Readiness

### What Needs to Be Done

1. **T1**: Create `backend/migrations/versions/018_fix_user_profile_fk.py`
   - Backfill user_account for existing profile user_ids
   - Drop FK constraint to `app_user.id`
   - Create FK constraint to `user_account.id`

2. **T2**: Update `backend/kernel/user/models/user_profile.py`
   - Change `ForeignKey("app_user.id")` → `ForeignKey("user_account.id")`

3. **T3**: Create `backend/migrations/versions/019_user_profile_permissions.py`
   - Insert `user_profile.create` permission (idempotent)
   - Map permissions to all roles:
     - Admin/client_director/institution_admin: create + read + update
     - Teacher/Staff/Student/Parent: read + update
   - Use `ON CONFLICT DO NOTHING` for idempotency

4. **T4**: Update `backend/kernel/authz/dependencies.py`
   - Reorder `_check_impl`: ownership check BEFORE Casbin
   - When `owner_id == ctx.user_id`, return immediately (skip Casbin)
   - When `owner_id != ctx.user_id`, run Casbin check

5. **T5-T7**: Update `backend/kernel/user/routes/profiles.py`
   - Add `owner_id=user_id` to `require_permission` in `create_profile`
   - Replace `obj_client_id/obj_institution_id` with `owner_id=user_id` in `get_profile`
   - Replace `obj_client_id/obj_institution_id` with `owner_id=user_id` in `update_profile`

6. **T8**: Add tests to `backend/tests/test_c02_user.py`
   - Test class `TestUserProfileOwnership` with scenarios T-1 to T-11
   - Migration test scenarios MT-1 to MT-5

### Verification Commands (to run after implementation)

```bash
# Run migrations
alembic upgrade head

# Run tests
pytest backend/tests/test_c02_user.py -v
pytest backend/tests/test_c04_authz.py -v

# Check for regressions
pytest backend/tests/ -v

# Verify git status
git status
git diff --stat
```

---

## 6. Acceptance Criteria Traceability

| AC | Criterion | Status | Evidence |
|----|-----------|--------|----------|
| AC-1 | `UserProfile.user_id` FK references `user_account.id` | ❌ | Model still references `app_user.id` |
| AC-2 | All roles have `user_profile.read` and `user_profile.update` | ❌ | Missing for Admin, institution_admin, Teacher, Staff, Student, Parent |
| AC-3 | Admin/CD/institution_admin have `user_profile.create` | ❌ | Missing for Admin, institution_admin (CD has read/update only) |
| AC-4 | POST allows self-creation without `user_profile.create` | ❌ | `_check_impl` ordering blocks this |
| AC-5 | PATCH passes `owner_id=user_id` — self-only for non-admin | ❌ | Route uses `obj_client_id/obj_institution_id` |
| AC-6 | GET passes `owner_id=user_id` — self-only for non-admin | ❌ | Route uses `obj_client_id/obj_institution_id` |
| AC-7 | Admin can create/update any profile (institution scope) | ⚠️ | Works if permissions mapped, but not verified |
| AC-8 | CD user can have UserProfile (FK fix) | ❌ | FK not changed |

---

## 7. Risk Assessment

| Risk | Severity | Current State | Mitigation |
|------|----------|---------------|------------|
| Self-creation blocked for non-admin users | **HIGH** | Confirmed — Casbin-first ordering fails for users without `user_profile.create` | Reorder `_check_impl` to check ownership before Casbin |
| CD users cannot have profiles | **HIGH** | Confirmed — FK references `app_user.id` | Change FK to `user_account.id` (migration 018) |
| Cross-user profile access (any user with permission can read/update any profile) | **HIGH** | Confirmed — no ownership check on routes | Add `owner_id=user_id` to all routes |
| Missing role-permission mappings | **MEDIUM** | Confirmed — only client_director has user_profile permissions | Create migration 019 |
| `_check_impl` reordering breaks existing callers | **LOW** | Unverified — all existing callers pass `owner_id=None` | Verify existing test suite passes after change |

---

## 8. Conclusion

**Implementation Status: ❌ NOT COMPLETE**

The `fix-user-profile-ownership` change has been specified (PRD, proposal, specs, design, tasks) but **not implemented**. Zero of8 tasks (T1-T8) have been completed. The core issues (FK target, ownership ordering, route changes, permission mappings) remain unresolved.

**Next Steps:**
1. Execute tasks T1-T8 in order (per design.md §10)
2. Run verification commands
3. Re-verify with this checklist
4. Proceed to ARCHIVE phase only when all ACs are satisfied

---

## 9. Acceptance Report

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "not_satisfied",
      "evidence": "Implementation not executed. All8 tasks (T1-T8) remain incomplete. FK target unchanged, ownership check ordering wrong, routes missing owner_id parameter, migrations not created, tests not added."
    }
  ],
  "changedFiles": [
    "openspec/changes/fix-user-profile-ownership/verify.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "git status",
      "result": "passed",
      "summary": "No staged files outside change scope"
    },
    {
      "command": "git diff --staged --stat",
      "result": "passed",
      "summary": "No staged changes detected"
    },
    {
      "command": "grep -n ForeignKey app_user.id user_profile.py",
      "result": "confirmed",
      "summary": "FK still references app_user.id (line22)"
    },
    {
      "command": "grep -n owner_id profiles.py",
      "result": "confirmed",
      "summary": "No owner_id parameter in routes"
    },
    {
      "command": "ls backend/migrations/versions/018* 019*",
      "result": "confirmed",
      "summary": "Migrations018 and019 do not exist"
    },
    {
      "command": "grep -n TestUserProfileOwnership test_c02_user.py",
      "result": "confirmed",
      "summary": "No ownership test class exists"
    }
  ],
  "validationOutput": [
    "Model validation: user_profile.py:22 still has ForeignKey('app_user.id') — NOT changed to user_account.id",
    "Authorization logic: dependencies.py _check_impl runs Casbin BEFORE ownership check — ordering is wrong per design",
    "Route validation: profiles.py create_profile/get_profile/update_profile all lack owner_id parameter",
    "Migration validation: No migration 018 (FK change) or 019 (role permissions) found in backend/migrations/versions/",
    "Test validation: No TestUserProfileOwnership class or ownership test scenarios in test_c02_user.py",
    "Permission mapping: Only client_director has user_profile.read/update (migration 016). Admin, institution_admin, Teacher, Staff, Student, Parent lack permissions."
  ],
  "residualRisks": [
    "HIGH: Self-creation blocked for non-admin users (Casbin-first ordering fails without user_profile.create permission)",
    "HIGH: CD users cannot have profiles (FK references app_user.id, not user_account.id)",
    "HIGH: Cross-user profile access possible (no ownership check on routes)",
    "MEDIUM: Missing role-permission mappings for Admin, institution_admin, Teacher, Staff, Student, Parent",
    "LOW: _check_impl reordering may affect existing callers (owner_id=None preserves behavior)"
  ],
  "noStagedFiles": true,
  "diffSummary": "No implementation changes made. Only openspec verification artifact created (verify.md). All8 implementation tasks (T1-T8) remain incomplete.",
  "reviewFindings": [
    "blocker: user_profile.py:22 — FK still references app_user.id (should be user_account.id)",
    "blocker: dependencies.py:60-80 — _check_impl runs Casbin before ownership check (should be reversed)",
    "blocker: profiles.py:28-30 — create_profile lacks owner_id parameter",
    "blocker: profiles.py:40-50 — get_profile uses obj_client_id/obj_institution_id instead of owner_id",
    "blocker: profiles.py:55-65 — update_profile uses obj_client_id/obj_institution_id instead of owner_id",
    "blocker: migrations/versions/ — migration 018_fix_user_profile_fk.py does not exist",
    "blocker: migrations/versions/ — migration 019_user_profile_permissions.py does not exist",
    "blocker: test_c02_user.py — no TestUserProfileOwnership class or ownership test scenarios"
  ],
  "manualNotes": "This is a VERIFY-only assessment. No implementation was attempted. All8 tasks (T1-T8) from tasks.md must be executed before this change can proceed to ARCHIVE. The change requires modifications to6 files (2 new migrations, 1 model update, 1 dependency update, 1 route update, 1 test file). Environment for running tests requires Supabase PostgreSQL instance (not available in current environment)."
}
```
