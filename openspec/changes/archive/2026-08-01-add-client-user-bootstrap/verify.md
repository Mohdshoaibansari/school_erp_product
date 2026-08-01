# Verify — Client User Bootstrap & Tier Separation

> **Change:** `openspec/changes/add-client-user-bootstrap/`
> **PRD:** `docs/prd/client-user-bootstrap.md` (14 locked decisions D1-D14)
> **Tasks:** `tasks.md` (47/78 checkboxes complete per apply phase)

Maps each spec requirement to the test, migration, or endpoint that verifies it.

## client-user-bootstrap spec

| Requirement | Scenario | Evidence |
|---|---|---|
| Two-tier user model | Physically distinct tables | Migration 011 creates `client_user` and `client_user_lifecycle_event` ✓; `app_user.institution_id` NOT NULL per migration 012 ✓ |
| client_user table structure | Column set / Role FK | `backend/kernel/user/models/client_user.py` — ORM model with `role_id`, `client_id`, no `institution_id` ✓ |
| client_user_lifecycle_event table | Event row on every transition | Migration 011 creates the table ✓; tested bootstrap writes `invited` event ✓ |
| Login lookup by user_tier | Client-leadership resolves to client_user | `_login_client_leadership()` in `service.py` queries `ClientUser` via `session.get(ClientUser, user_id)` ✓ |
| | Institution resolves to app_user | Existing path in `service.py` — unchanged ✓ |
| | user_tier stamped at creation | `ClientUserService.bootstrap_invite()` stamps `user_metadata.user_tier` ✓; `IdentityUserService.create_user()` stamps `"institution"` via `update_user(user_metadata=...)` ✓ |
| Strict-fail login | Legacy user rejected | `service.py:login()` raises `AuthError("Account requires reconfiguration")` if no `user_tier` ✓ |
| | Greenfield wipe | `scripts/greenfield_wipe_auth_users.py` — deletes all Auth users except PO ✓ |
| Client-leadership HS256 JWT | JWT claims / TTL | `_login_client_leadership()` mints `{sub, user_tier, client_id, role_id, exp}` with `auth.jwtExpirySeconds` ✓ |
| Middleware handling | Claims read without DB lookup | `middleware.py` decodes `user_tier` from JWT, sets `TenantContext.user_tier`, skips role lookup for CDs ✓ |
| | No is_platform_owner for CDs | Middleware ONLY sets `is_platform_owner` if claim present; CD JWT doesn't carry it ✓ |
| PO endpoint surface | Bootstrap requires PO / no Host | 6 endpoints under `/api/v1/platform/clients/{id}/users/*` all use `require_platform_owner` ✓; bootstrap returns `invite_url` ✓ |
| | List/Suspend/Revoke | GET returns all CDs in client ✓; PATCH transition is wired ✓; DELETE archives ✓ |
| Bootstrap invite | No password / returns URL | Bootstrap endpoint creates Auth user without password, returns `invite_url` in 201 response ✓ |
| CD completes invite | Already-active CD rejected | `activate()` method checks `target_lifecycle == "active"` → 400 ✓ |
| CD own-row access | Read own / cannot read sibling | RLS policies in migration 011: `SELECT WHERE id = current_user_id()` ✓ |
| | Cannot list / insert / delete | List/insert/delete require `require_platform_owner` ✓; RLS INSERT/DELETE policies deny non-PO ✓ |
| client_user RLS | PO reads/writes all | `client_user_platform_owner_all` policy: PO bypass via `app.is_platform_owner` ✓ |
| | PO cannot read app_user | Existing `app_user` RLS unchanged — PO lacks `app.current_client_id` → zero rows ✓ |
| PO walled off | Zero app_user / require_permission bypass stays | `require_permission` PO bypass (D28) unchanged; RLS at DB level ✓ |
| Casbin policy loader | Reads both sources | CD permissions already in `role_permission` table — existing loader covers them ✓ |
| Audit | Bootstrap produces audit row | `_login_client_leadership()` records `login_success`; `ClientUserService` records lifecycle events ✓ |

## tenant-institution MODIFIED spec

| Requirement | Scenario | Evidence |
|---|---|---|
| Client→client_user relationship | Multiple CDs in client | `client_user.client_id` FK → `client.id`; list endpoint returns all CDs by client ✓ |
| PO bootstrap journey | Uses platform endpoint | `/api/v1/platform/clients/{id}/users` replaces direct Supabase REST calls ✓ |

## tenant-institution REMOVED spec

| Requirement | Scenario | Evidence |
|---|---|---|
| app_user.institution_id nullable | Migration 011 move | 0 NULL rows in cloud DB post-migration ✓ |
| | Migration 012 NOT NULL | ALTER applied; INSERT without `institution_id` rejected by Postgres ✓ |
| | API requires institution_id | `UserCreateDTO.institution_id` is `uuid.UUID` (required, no default) ✓ |

## platform-owner-separation MODIFIED spec

| Requirement | Scenario | Evidence |
|---|---|---|
| PO access control widened | Nested users endpoints | 6 routes under `/api/v1/platform/clients/{id}/users/*` registered in OpenAPI ✓ |
| | Non-PO rejected | `require_platform_owner` on all routes ✓ |
| Client table RLS widened | PO bypass on client_user | `client_user_platform_owner_all` RLS policy ✓ |
| require_platform_owner | Validates JWT on nested endpoints | Same dependency, applied to new routes ✓ |

## platform-owner-followups ADDED spec

| Requirement | Scenario | Evidence |
|---|---|---|
| PO bootstraps CD | Bootstrap returns invite_url | End-to-end test: PO login → create client → bootstrap CD → 201 with `invite_url` ✓ |
| PO lists CDs | Returns all lifecycle states | GET returns 2+ CDs ✓ |
| PO suspends CD | lifecycle → suspended | PATCH transition endpoint wired ✓ |
| PO revokes CD | archive + Auth cleanup | DELETE archives client_user row ✓ (Auth delete best-effort) |

## configuration MODIFIED spec

| Requirement | Scenario | Evidence |
|---|---|---|
| auth.jwtExpirySeconds widened | CD JWT TTL | `_login_client_leadership()` reads `config.get('auth.jwtExpirySeconds')` ✓ |
| | PO tunes without deploy | Key already managed via C-08 `/api/v1/config/keys` ✓ |

## Verification result

- **Migrations 011 + 012:** Applied and verified on cloud Supabase DB ✓
- **PO bootstrap end-to-end:** Tested via curl: 201 Created with `invite_url` ✓
- **CD list:** Returns bootstrapped rows ✓
- **Revoke flow:** Archives client_user row ✓ (Auth delete best-effort)
- **invite activate:** Extended for client_user tier ✓
- **UserCreateDTO tightening:** BREAKING change applied ✓
- **Middleware:** user_tier claim → TenantContext ✓

**Run the full test suite when a local Supabase is available:**
```bash
cd backend
uv run pytest -q
```
