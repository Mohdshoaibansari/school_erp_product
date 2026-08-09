# Proposal — C-02 User Service Strategy Pattern Refactor

> **Change:** `refactor-c02-user-service-strategy-pattern`
> **Decisional source:** `docs/architecture/adr-c02-identity-user-management-implementation.md` (D6-D10 added 2026-08-03)
> **Audit source:** `docs/architecture/audit-c02-implementation-2026-08-03.md`
> **Predecessor change:** `add-c02-user-creation-activation` (currently in flight, PARTIAL verify)

## Why

The 2026-08-03 integration audit of the C-02 implementation revealed:

- **CRITICAL** — missing cross-tenant check on CD login (tenant isolation bug)
- **MAJOR** — response-shape asymmetry between the two user tiers (CD returns `{user_id, email, invite_url, client_id}`, institution returns `{user, invite_url}`); audit emission missing on CD bootstrap; transaction-order inconsistencies (commit AFTER Supabase call, role validation AFTER Supabase create)
- **P1 runtime bugs** — `request_otp` NameError, `TokenResponse` strips tier fields, `app.current_institution_id` not set in RLS hook, migration 012 untracked in git
- **Structural drift** — two parallel service classes (`IdentityUserService` for app_user, `ClientUserService` for client_user) with diverging method shapes, response contracts, and audit emissions — a patched state that doesn't honor the ADR's D1-D5 unification intent

The grill-me session on 2026-08-03 concluded that the asymmetries are not intentional — they are patched-state artifacts. The architectural direction is:

1. **Replace both services with a single `UserService`** (D6)
2. **Keep `AuthService` separate** for login, refresh, logout, activate, OTP, password-reset (D6)
3. **`StrategyResolver` inside `UserService`** — DTO type for create, DB lookup for others; long-term evolution to `Organization.type` via `Membership` (D7)
4. **Full-symmetric strategy interface** — every method on both strategies (D8)
5. **Unified `LoginResponse` model** with optional tier fields (D9)
6. **All 10 audit bugs folded into the refactor** (D10)

## What changes

### Code surface (all in `backend/kernel/`)

| File | What happens |
|---|---|
| `kernel/user/services/service.py` | Becomes the new unified `UserService`. Contains `StrategyResolver`, `CDStrategy`, `InstitutionUserStrategy`. |
| `kernel/user/services/client_user_service.py` | Deleted. Its logic is split between `CDStrategy` (PO bootstrap, CD row CRUD) and `UserService` (CD lifecycle transitions, role assignment). |
| `kernel/user/services/dtos.py` | `UserCreateResponseDTO` extends to support both tiers (already done). New: `UserService` returns this. `UserDTO` unchanged. `LoginResponse` is added (in `kernel/auth/services/dtos.py` or `kernel/auth/routes/auth.py`). |
| `kernel/auth/services/service.py` | `AuthService` keeps login/refresh/logout/activate/OTP/password-reset. The login method now dispatches to a tier-specific JWT-minting strategy internally (PO custom HS256, CD custom HS256, institution Supabase). Activate and login are reconciled to use the same cross-tenant check. |
| `kernel/auth/supabase_client.py` | `update_user` signature already has `user_metadata` parameter (Fix #1). |
| `kernel/db.py` | RLS hook adds `app.current_institution_id` (D10 bug #3). |
| `kernel/user/dependencies.py` | DI returns the new `UserService` (replaces `IdentityUserService`). |
| `kernel/business/tenant_institution/dependencies.py` | DI returns the new `UserService` for the PO bootstrap route. |
| `kernel/auth/dependencies.py` | DI returns the existing `AuthService` (no change). |
| `tests/fake_supabase_auth.py` | `update_user` uses overwrite (not merge) — matches real impl. `user_metadata` stored + returned (already done). |
| `tests/test_c02_user.py` | Updated to mock the new strategy resolution. Test fixtures use the new DTO shapes. |
| `tests/test_c03_auth.py` | Updated to mock the new `LoginResponse` shape. |

### Migration

- `backend/migrations/versions/012_app_user_institution_id_not_null.py` — must be committed to git (bug #7).
- No new migration required for D6-D10. The schema doesn't change.

## Out of scope

- The strategy pattern for `Organization.type` via `Membership` (long-term D7 target) — the resolver currently uses DTO type and DB lookup. Membership model is a future capability.
- Email delivery of invite links (C-09).
- Bulk user import.
- Self-registration of Client Directors (D6 from the bootstrap PRD is preserved as a non-goal).

## Cross-references

- ADR: `docs/architecture/adr-c02-identity-user-management-implementation.md` (D6-D10 sections)
- Audit: `docs/architecture/audit-c02-implementation-2026-08-03.md`
- Predecessor change: `openspec/changes/add-c02-user-creation-activation/`
