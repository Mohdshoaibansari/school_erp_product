# Platform Owner Separation — Spec

## Summary

Separate platform owner from tenant-scoped `app_user` table. Platform owner exists only in Supabase Auth with `user_metadata.is_platform_owner = true`. No domain binding, no institution access.

## Decisions (D1–D36)

### Identity & Storage

| # | Decision |
|---|----------|
| D1 | Platform owner only in Supabase Auth (`user_metadata.is_platform_owner = true`), NOT in `app_user` |
| D7 | Delete existing platform owner from `app_user` + `role_assignment`, create fresh in Supabase Auth |
| D27 | New email `admin@school-erp.com` for platform owner. Deprecate `platform@test-school.com` |
| D28 | Password `Shoby@123` hardcoded in migration script |
| D6 | Platform owner created manually via Supabase Dashboard (documented steps) |
| D15 | One-time migration script for transition |

### Authentication

| # | Decision |
|---|----------|
| D2 | Login: if `user_metadata.is_platform_owner = true`, skip `app_user` lookup, return platform token |
| D3 | JWT: `sub` (user_id) + `is_platform_owner: true` claim |
| D8 | Middleware skips subdomain resolution for platform owner (no Host header needed) |
| D16 | Auth service checks Supabase Auth metadata during login, adds `is_platform_owner` to JWT |
| D25 | Auth service uses `SupabaseAuthClient.get_user()` for metadata |
| D26 | Auth service calls Supabase Auth Admin API directly for full user object |
| D35 | Login response: `is_platform_owner: true` only for platform owner |

### Authorization

| # | Decision |
|---|----------|
| D4 | Platform owner bypasses Casbin entirely via `is_platform_owner=True` |
| D5 | Middleware blocks platform owner from endpoints requiring `client_id` |
| D9 | Platform owner detected ONLY from JWT claim. Remove role lookup + path prefix detection |
| D10 | Platform owner: `roles = []` in TenantContext |
| D11 | `require_platform_owner` checks JWT claim directly (not TenantContext) |
| D13 | `require_permission`: `is_platform_owner=True` skips Casbin (current behavior) |
| D20 | `require_permission` stays as-is |
| D22 | Platform owner only accesses `/api/v1/platform/...` endpoints |

### Tenant Context & Filtering

| # | Decision |
|---|----------|
| D18 | Middleware whitelist for paths not requiring `client_id` |
| D19 | `TenantContext` stays as-is. `client_id=None` for platform owner |
| D21 | `list_users` skips tenant filter for platform owner |
| D23 | Whitelist configurable via `backend/config.py` |
| D36 | Repo base class checks `ctx.is_platform_owner`, skips tenant filter if true |

### Database

| # | Decision |
|---|----------|
| D14 | Add RLS to `client` table with `app.is_platform_owner = true` bypass policy |

---

## Implementation Changes

### 1. Config (`backend/config.py`)

Add whitelist of paths that don't require `client_id`:

```python
PLATFORM_PATHS = ["/api/v1/platform/", "/api/auth/", "/health"]
```

### 2. Middleware (`kernel/middleware.py`)

- **D9**: Remove role lookup for `platform_owner`. Remove path prefix detection.
- **D8**: If JWT has `is_platform_owner: true`, skip subdomain resolution. Set `TenantContext(is_platform_owner=True, client_id=None, institution_id=None)`.
- **D5/D18**: Check whitelist. If path is in whitelist and `is_platform_owner=True`, allow without `client_id`.

### 3. Auth Service (`kernel/auth/services/service.py`)

- **D2/D16/D26**: After Supabase Auth login success, call Supabase Auth Admin API to get user metadata.
- If `user_metadata.is_platform_owner = true`:
  - Skip `app_user` lookup
  - Add `is_platform_owner: true` to JWT payload
  - Return `is_platform_owner: true` in login response (D35)

### 4. Auth Dependencies (`kernel/authz/dependencies.py`)

- **D11/D24**: `require_platform_owner` reads JWT from `Authorization` header, decodes it, checks `is_platform_owner: true` claim directly.

### 5. Repo Base (`kernel/repo_base.py`)

- **D36**: `_base_query` checks `ctx.is_platform_owner`. If true, skip tenant filter.

### 6. User Routes (`kernel/user/routes/users.py`)

- **D21**: `list_users` checks `ctx.is_platform_owner`. If true, skip tenant filter.

### 7. Database Migration (`migrations/versions/007_platform_owner_rls.py`)

- **D14**: Add RLS to `client` table with `app.is_platform_owner = true` bypass policy.

### 8. Migration Script (`scripts/migrate_platform_owner.py`)

- **D7/D15/D17/D27/D28**:
  1. Delete existing platform owner from `role_assignment` + `app_user`
  2. Create new Supabase Auth user via Admin API with `user_metadata.is_platform_owner = true`
  3. Email: `admin@school-erp.com`, Password: `Platform@2026!`

---

## Acceptance Criteria

1. Platform owner can login without Host header
2. Platform owner gets JWT with `is_platform_owner: true`
3. Platform owner can access `/api/v1/platform/clients` (list all clients)
4. Platform owner cannot access `/api/v1/users` (returns 403)
5. Platform owner has no `app_user` row
6. Normal users unaffected — all existing tests pass
