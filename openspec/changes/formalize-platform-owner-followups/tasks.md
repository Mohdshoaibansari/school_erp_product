# Tasks — Formalize Platform Owner Followups

> Documentation-only change. All 7 items being formalized are already implemented
> on `main` and live on cloud Supabase. Tasks below are **verification tasks**, not
> implementation tasks.

## 1. Verification — Middleware role resolution

- [ ] 1.1 Verify `Kernel/middleware.py` role lookup for non-platform-owner users works (test: normal user login → roles populated)
- [ ] 1.2 Verify platform owner is excluded from `app_user`-based role lookup (test: platform owner login → `roles=[]`)
- [ ] 1.3 Verify Host-header fallback to `app_user` client_id works (test: Swagger UI login without Host → roles resolved)
- [ ] 1.4 Verify subdomain takes precedence over fallback when both are present (test: curl with Host → subdomain's client_id used)

## 2. Verification — Cross-cutting refactors

- [ ] 2.1 Verify `GET /api/v1/lookups/institution-types` returns list of institution types with `{id, code}`
- [ ] 2.2 Verify `GET /api/v1/lookups/org-unit-types` returns list of org unit types with `{id, name}`
- [ ] 2.3 Verify `POST /api/v1/submissions/{id}/grade` works without `NameError` (test: teacher grades submission → 200)
- [ ] 2.4 Verify `SupabaseAuthClientImpl.create_user` uses `httpx` (test: source code review of `kernel/auth/supabase_client.py`)

## 3. Verification — Client Director lifecycle support

- [ ] 3.1 Verify `client_director` role has `institution.create` permission in `role_permission` table
- [ ] 3.2 Verify `app_user.institution_id` is nullable (test: `INSERT INTO app_user (..., institution_id=NULL, ...)` succeeds)
- [ ] 3.3 Verify `Admin` role does NOT have `institution.create` permission (test: admin attempts institution creation → 403)
- [ ] 3.4 Verify Client Director can list users in own client (test: client_director → `GET /api/v1/users` returns users for that client only)
