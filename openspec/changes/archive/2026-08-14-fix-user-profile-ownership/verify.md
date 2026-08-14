# Verify — fix-user-profile-ownership

> **Change ID:** fix-user-profile-ownership
> **Capability:** C-02 Identity & User Management (intersecting C-04 Authorization)
> **Status:** Verification
> **Created:** 2026-08-12
> **Last updated:** 2026-08-13
> **Verified against:** Current `main` branch state

---

## 1. Spec-to-Task Mapping

### Identity-User-Management Spec

| Requirement | Task(s) | Status | Evidence |
|-------------|---------|--------|----------|
| **UserProfile FK to user_account** | T1 (Migration 018), T2 (Model update) | ❌ NOT IMPLEMENTED | `user_profile.py:22` still has `ForeignKey("app_user.id")`. No migration 018 file exists. |
| **Self-Service Profile Management (Stage 3 Bypass)** | T4 (`_check_impl` update), T5-T7 (Route changes) | ❌ NOT IMPLEMENTED | Routes don't pass `owner_id=user_id`. Stage 3 bypass exists in `_check_impl` but routes don't trigger it. |
| **Admin Profile Management (user_profile.admin)** | T3 (Migration 019), T5-T7 (Route changes) | ❌ NOT IMPLEMENTED | `user_profile.admin` permission doesn't exist. Routes use `user_profile.create/read/update` actions instead of `admin`. |
| **Non-Admin Cross-User Access Denied** | T5-T7 (Route changes) | ❌ NOT IMPLEMENTED | Routes lack `owner_id` parameter, so cross-user access is not properly gated. |
| **Duplicate Profile Rejection** | T5 (create_profile route) | ⚠️ PARTIALLY DONE | Depends on existing service logic; needs verification. |

### Authorization Spec

| Requirement | Task(s) | Status | Evidence |
|-------------|---------|--------|----------|
| **New user_profile.admin Permission** | T3 (Migration 019) | ❌ NOT IMPLEMENTED | `user_profile.admin` does not exist in the permission table. |
| **Role-Permission Mapping for user_profile.admin** | T3 (Migration 019) | ❌ NOT IMPLEMENTED | No migration 019 exists for `user_profile.admin` role mappings. |
| **Remove Stage 5 from _check_impl** | T4 | ❌ NOT IMPLEMENTED | Stage 5 (ownership/admin bypass) still exists in `_check_impl` after Casbin check. |
| **Profile Routes Use user_profile.admin** | T5-T7 | ❌ NOT IMPLEMENTED | Routes use `user_profile.create/read/update` actions, not `admin`. |

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

**Current flow:**
```
1. Platform owner bypass
2. Role validation
3. Self-service bypass (Stage 3) — owner_id == ctx.user_id → PASS
4. Casbin enforcement (Stage 4)
5. Ownership/admin bypass (Stage 5) ← SHOULD BE REMOVED
```

**Required flow:**
```
1. Platform owner bypass
2. Role validation
3. Self-service bypass (Stage 3) — owner_id == ctx.user_id → PASS
4. Casbin enforcement (Stage 4) — result is authoritative
(NO Stage 5)
```

**Impact:** Stage 5 is dead code for the new two-tier model. Casbin at Stage 4 handles admin access via `user_profile.admin`.

---

### 2.3 Routes — `backend/kernel/user/routes/profiles.py`

| Endpoint | Current Auth Check | Required Auth Check |
|----------|-------------------|---------------------|
| `POST /api/v1/users/{id}/profile` | `require_permission("user_profile", "create")` | `require_permission("user_profile", "admin", owner_id=user_id)` |
| `GET /api/v1/users/{id}/profile` | `check_permission(ctx, enforcer, "user_profile", "read", obj_client_id=..., obj_institution_id=...)` | `check_permission(ctx, enforcer, "user_profile", "admin", owner_id=user_id)` |
| `PATCH /api/v1/users/{id}/profile` | `check_permission(ctx, enforcer, "user_profile", "update", obj_client_id=..., obj_institution_id=...)` | `check_permission(ctx, enforcer, "user_profile", "admin", owner_id=user_id)` |

---

### 2.4 Migrations

| Migration | Status | Evidence |
|-----------|--------|----------|
| `018_fix_user_profile_fk.py` | ❌ DOES NOT EXIST | Not found in `backend/migrations/versions/` |
| `019_user_profile_admin_permission.py` | ❌ DOES NOT EXIST | Not found in `backend/migrations/versions/` |

---

### 2.5 Tests

| Test Category | Status | Evidence |
|---------------|--------|----------|
| Self-service tests (T-1 to T-3) | ❌ NOT ADDED | No self-service test scenarios in `test_c02_user.py` |
| Admin tests (T-7 to T-9) | ❌ NOT ADDED | No admin test scenarios |
| Cross-user denial tests (T-4 to T-6) | ❌ NOT ADDED | No cross-user denial test scenarios |
| Migration tests (MT-1 to MT-5) | ❌ NOT ADDED | No migration test scenarios |

---

## 3. Gap Summary

### Critical Gaps (Blocking)

1. **FK not changed**: UserProfile still references `app_user.id`, blocking CD users (AC-1, AC-7)
2. **Stage 5 not removed**: Ownership/admin bypass still exists in `_check_impl` (AC-6)
3. **Routes missing `owner_id`**: All three endpoints lack `owner_id=user_id` parameter (AC-3, AC-4, AC-5)
4. **Routes use wrong action**: Routes use `create/read/update` instead of `admin` for Casbin (AC-2, AC-4)

### High Gaps

5. **Missing `user_profile.admin` permission**: Permission doesn't exist in the database (AC-2)
6. **Missing role mappings**: Admin/CD/institution_admin not mapped to `user_profile.admin` (AC-2)
7. **Missing migrations**: Both migration 018 and 019 don't exist

### Medium Gaps

8. **No tests**: Zero test coverage for the two-tier model (T-1 to T-11, MT-1 to MT-5)

---

## 4. Post-Implementation Checklist

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | `UserProfile.user_id` FK references `user_account.id` | ❌ | Model not updated, migration not created |
| 2 | `user_profile.admin` permission exists | ❌ | Migration 019 not created |
| 3 | Admin/CD/institution_admin have `user_profile.admin` | ❌ | Migration 019 not created |
| 4 | Stage 5 removed from `_check_impl` | ❌ | Stage 5 still present |
| 5 | All routes pass `owner_id=user_id` | ❌ | Routes not updated |
| 6 | All routes use action=`"admin"` | ❌ | Routes use `create/read/update` |
| 7 | Self-service bypass works (Stage 3) | ⚠️ | Stage 3 exists but routes don't trigger it |
| 8 | Admin can manage any profile (Stage 4) | ❌ | `user_profile.admin` not in Casbin |
| 9 | Non-admin blocked for cross-user | ❌ | Routes don't enforce ownership |
| 10 | CD user can have UserProfile (FK fix) | ❌ | FK not changed |
| 11 | Migration 018 applies cleanly | N/A | Migration doesn't exist |
| 12 | Migration 019 inserts `user_profile.admin` | N/A | Migration doesn't exist |
| 13 | Migration 019 is idempotent | N/A | Migration doesn't exist |
| 14 | Self-service tests pass (T-1 to T-3) | ❌ | Tests not created |
| 15 | Admin tests pass (T-7 to T-9) | ❌ | Tests not created |
| 16 | Cross-user denial tests pass (T-4 to T-6) | ❌ | Tests not created |
| 17 | Migration tests pass (MT-1 to MT-5) | ❌ | Tests not created |
| 18 | Existing test suite passes (no regressions) | ⚠️ | Cannot verify without running tests |
| 19 | No staged files outside change scope | ✅ | Git status clean |

---

## 5. Implementation Readiness

### What Needs to Be Done

1. **T1**: Create `backend/migrations/versions/018_fix_user_profile_fk.py`
   - Backfill user_account for existing profile user_ids
   - Drop FK constraint to `app_user.id`
   - Create FK constraint to `user_account.id`

2. **T2**: Update `backend/kernel/user/models/user_profile.py`
   - Change `ForeignKey("app_user.id")` → `ForeignKey("user_account.id")`

3. **T3**: Create `backend/migrations/versions/019_user_profile_admin_permission.py`
   - Insert `user_profile.admin` permission (idempotent)
   - Map `user_profile.admin` to Admin (institution), client_director (tenant), institution_admin (institution)

4. **T4**: Update `backend/kernel/authz/dependencies.py`
   - Remove Stage 5 (ownership/admin bypass) from `_check_impl`
   - Keep Stage 3 (self-service bypass) and Stage 4 (Casbin) only

5. **T5-T7**: Update `backend/kernel/user/routes/profiles.py`
   - Add `owner_id=user_id` to all 3 endpoints
   - Change action from `create/read/update` to `admin`

6. **T8**: Add tests to `backend/tests/test_c02_user.py`
   - Self-service tests (T-1 to T-3)
   - Cross-user denial tests (T-4 to T-6)
   - Admin tests (T-7 to T-9)
   - Migration tests (MT-1 to MT-5)

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
| AC-2 | `user_profile.admin` exists and mapped to admin roles | ❌ | Permission and mappings don't exist |
| AC-3 | All roles can manage own profile (Stage 3) | ❌ | Routes don't pass `owner_id` |
| AC-4 | Admin/CD/institution_admin can manage any profile | ❌ | Routes don't use `user_profile.admin` |
| AC-5 | Teacher CANNOT manage another teacher's profile | ❌ | Routes don't enforce ownership |
| AC-6 | Stage 5 removed from `_check_impl` | ❌ | Stage 5 still present |
| AC-7 | CD user can have UserProfile (FK fix) | ❌ | FK not changed |

---

## 7. Risk Assessment

| Risk | Severity | Current State | Mitigation |
|------|----------|---------------|------------|
| Stage 5 removal breaks other resources | **Low** | Stage 5 only runs when `owner_id` is set; only profile routes pass it | Verify existing test suite passes |
| CD users cannot have profiles | **HIGH** | Confirmed — FK references `app_user.id` | Change FK to `user_account.id` (migration 018) |
| Cross-user profile access | **HIGH** | Confirmed — no ownership check on routes | Add `owner_id=user_id` to all routes |
| Missing `user_profile.admin` permission | **HIGH** | Confirmed — permission doesn't exist | Create migration 019 |
| `_check_impl` Stage 5 dead code | **Low** | Confirmed — Stage 5 runs after Casbin but is redundant | Remove Stage 5 |

---

## 8. Conclusion

**Implementation Status: ❌ NOT COMPLETE**

The `fix-user-profile-ownership` change has been specified (PRD, proposal, specs, design, tasks) but **not implemented**. All 8 tasks (T1-T8) remain incomplete. The core issues (FK target, Stage 5 removal, route changes, `user_profile.admin` permission) remain unresolved.

**Next Steps:**
1. Execute tasks T1-T8 in order (per design.md §9)
2. Run verification commands
3. Re-verify with this checklist
4. Proceed to ARCHIVE phase only when all ACs are satisfied
