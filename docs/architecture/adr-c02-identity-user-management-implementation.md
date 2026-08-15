# C-02 Identity & User Management — User Creation & Activation Decisions

> **Status:** Final
> **Version:** 1.0
> **Last Updated:** 2026-08-03
> **Author:** Architecture (collaborative grill-me session)
> **Source:** [platform-capabilities-v3.md](../platform-capabilities/platform-capabilities-v3.md) §C-02, §C-03; [architecture-v1.md](../reference/architecture-v1.md); [c-01 ADR](../architecture/adr-c01-tenant-institution-implementation.md); [client-user-bootstrap PRD](../../prd/client-user-bootstrap.md); grill-me session 2026-08-03
> **Purpose:** Capture the 5 implementation-level decisions for the unified user-creation-and-activation flow across both Client Director (client_user table) and institution-scoped users (app_user table). These decisions close gaps left by the existing bootstrap PRD and unify the two currently-disconnected creation-plus-activation paths.
> **Cross-References:**
> - [Platform Capabilities v3](../platform-capabilities/platform-capabilities-v3.md) §C-02 (Identity & User Management), §C-03 (Authentication)
> - [Architecture v1](../architecture-v1.md) §3, §5.3
> - [C-01 ADR](../architecture/adr-c01-tenant-institution-implementation.md) — tenant isolation, two-tier model
> - [Client User Bootstrap PRD](../../prd/client-user-bootstrap.md) — D1-D14 for client_user bootstrap
> - [Functional Requirements](../../requirements/functional-requirements.md) §1.3, §1.4

---

## 1. Context

The School ERP platform has two user populations that share a common need — creation by an authority followed by self-activation:

| User type | Creator | Table | Current state |
|-----------|---------|-------|---------------|
| Client Director (CD) | Platform Owner | `client_user` | Bootstrap via `POST /api/v1/platform/clients/{id}/users` returns an invite URL + token; activation via `POST /api/auth/activate`. |
| Institution user (Admin, Teacher, Student, Parent) | Client Director | `app_user` | Created via `POST /api/v1/users` — returns a `UserDTO` with **no invite token**. No backend activation endpoint exists for institution users; the journey-flow HTML workaround bypasses the backend entirely by calling the Supabase Admin API directly with the `service_role` key to set passwords and lifecycle status. |

This asymmetry is accidental, not intentional. The `/api/auth/activate` endpoint already contains code to handle both `client_user` and `app_user` tables (lines 355–395 of `service.py`). The only gap is that `POST /api/v1/users` does not mint an invite token.

Making these paths identical eliminates the Supabase Admin API workaround (which exposes `service_role` in the browser), gives every user the same creation→invite→activate lifecycle, and consolidates token minting into the single, well-tested `login()` method.

Three pre-existing production-breaking bugs sit on the activation path and must be resolved for any of this to work:

1. **`SupabaseAuthClientImpl.update_user` NameError** (`supabase_client.py` line 270): the method body references `user_metadata` but the implementation signature omits it.
2. **RLS session variables never set on endpoint sessions**: `app.is_platform_owner`, `app.current_client_id`, and `app.current_user_id` are only set on ephemeral lookup connections inside `_resolve_client_from_subdomain`, never on the actual database session used by endpoint dependencies. RLS policies on `client_user` (migration 011) and `app_user` (migration 001) reference these session variables, but they are always NULL at runtime.
3. **`app.current_user_id` never populated anywhere**: referenced by `client_user_cd_select_own` and `client_user_cd_update_own` RLS policies (migration 011 lines 78–95) but has no runtime code path that sets it. CD own-row access cannot work without it.

Tests hide bugs 2 and 3 because `conftest.py` line 142 sets `SET LOCAL app.is_platform_owner = 'true'` on every test session, masking the production gap.

---

## 2. Decision

Five decisions, each resolving one gap. Each sub-section states the resolution, the rationale, and the alternatives rejected.

### D1 — Unified activation flow for all user types

**Decision:** Every user, regardless of type (Client Director in `client_user` or institution user in `app_user`), follows the same creation + activation chain:

```
Creator calls POST /api/v1/.../users
        │
        ▼
  Backend creates: Supabase Auth user (no password)
                 + DB row (client_user or app_user, lifecycle="invited")
                 + mints invite JWT (HS256, 7-day expiry from config)
                 + returns invite_url containing the JWT
        │
        ▼
  Creator forwards invite link to the user (email or out-of-band)
        │
        ▼
  User clicks link → POST /api/auth/activate {invite_token, password}
        │
        ▼
  Backend verifies invite JWT
  Sets password in Supabase Auth (via update_user)
  Transitions lifecycle: invited → active
  Returns {message, user_id, user_tier, client_slug}
        │
        ▼
  Frontend redirects to {client_slug}.<host>/login
  User logs in with email + new password → receives JWT tokens
```

**Rationale:** `/api/auth/activate` already contains code to handle both `client_user` and `app_user` tables. The `POST /api/v1/users` endpoint currently creates the Supabase Auth user (via `IdentityUserService.create_user`) and inserts the `app_user` row, but does not mint an invite token. Adding invite-token minting to `create_user` is a small change that eliminates the entire Supabase Admin API workaround. A single activation path reduces test surface, audit complexity, and the risk of the two paths drifting apart.

The lifecycle for **both** user types is simplified to `invited → active`. The existing `pending` state for institution users (between invited and active) is preserved on the state machine for manual admin transitions (`POST /api/v1/users/{id}/transition`), but is removed from the normal activation flow — activate transitions directly to `active`.

**Alternatives rejected:**

| Alternative | Reason for rejection |
|---|---|
| Build a separate activation flow for institution users (Supabase email-confirmation + webhook) | Two code paths; delays parity; the activate endpoint already handles both tables |
| Keep the current Supabase Admin API workaround | Exposes `service_role` key in browser; no audit logging; no lifecycle validation |
| Have Admin set the password for institution users (no self-activation) | Poor security posture; doesn't match real-world expectations |
| Return JWT tokens from `/api/auth/activate` (immediate login) | Duplicates token-minting logic from `login()`; activate runs on platform URL with no subdomain context; login is the single source of truth for CD vs institution vs PO token minting |

---

### D2 — Role assigned at creation time

**Decision:** `POST /api/v1/users` (the institution-user creation endpoint) accepts an optional `role_id` field in the request body. When provided, the role is assigned atomically in the same transaction as user creation. The existing `POST /api/v1/users/{id}/roles` endpoint is preserved for later role changes (adding, removing, or updating role assignments).

The PO bootstrap endpoint `POST /api/v1/platform/clients/{id}/users` already accepts `role_id` in its request body (`ClientUserCreateDTO.role_id`). This decision extends the same pattern to institution users, making the two creation endpoints consistent.

**Rationale:** Currently, creating an institution user requires two API calls: create the user, then assign the role. Making `role_id` optional on creation allows one-call user provisioning. The existing `POST /api/v1/users/{id}/roles` endpoint is kept for subsequent role changes — it is not removed or deprecated.

**Alternatives rejected:**

| Alternative | Reason for rejection |
|---|---|
| Keep two-call create-then-assign pattern | Unnecessary round trip; the CDUI already knows the role at creation time |
| Remove `POST /api/v1/users/{id}/roles` | Users may need role changes later; keeping the endpoint costs nothing |
| Make `role_id` required | Some user creation scenarios may defer role assignment (e.g., bulk import). Optional keeps flexibility |

---

### D3 — Invite URL built from config key

**Decision:** The invite URL is built by concatenating a config key value with the token path. The config key `app.activationBaseUrl` (e.g., `"https://app.school-erp.com"`) is seeded via a new Alembic migration per AGENTS.md §8. The backend reads this key at runtime and constructs the invite URL as `{app.activationBaseUrl}/activate?token={invite_jwt}`.

The current hardcoded `frontend_url = "http://127.0.0.1:8000"` in `client_user_service.py` line 78 is replaced with a `config.get("app.activationBaseUrl")` call.

**Rationale:** Per AGENTS.md §8 (Config-First Module Development), URLs and environment-specific values must be config keys, not hardcoded. This lets local dev (`http://127.0.0.1:8000`), staging, and production (`https://app.school-erp.com`) all use the same code with different configuration.

**Alternatives rejected:**

| Alternative | Reason for rejection |
|---|---|
| Keep hardcoded `http://127.0.0.1:8000` | Fails in production; violates config-first rule |
| Return only the `invite_token` and let the frontend build the URL | Frontend needs to know the activate path; backend already has the config infrastructure |
| Use Supabase's built-in invite/confirmation flow | That flow doesn't transition our lifecycle states (invited → active); it only confirms email |

---

### D4 — Activate returns success only (no JWT tokens)

**Decision:** `POST /api/auth/activate` returns only `{message, user_id, user_tier, client_slug}`. It does NOT return access/refresh tokens. After activation, the frontend redirects the user to `{client_slug}.<host>/login`, where the user logs in with their email + newly-set password. The login endpoint is the single source of truth for token minting across all user types (PO, CD, institution user).

**Rationale:** The `login()` method in `service.py` contains non-trivial token-minting logic that branches per user type:
- Platform Owner → custom HS256 JWT with `{sub, is_platform_owner}`
- Client Director → custom HS256 JWT with `{sub, user_tier, client_id, role_id}`
- Institution user → Supabase access_token with roles looked up from DB

The activate endpoint runs on a platform path with no subdomain context. Having it also mint tokens would require duplicating the login branching logic in a place that lacks tenant context, lifecycle validation, and the cross-tenant guard. Keeping activation and login separate avoids this duplication and keeps the login method as the single entry point for authentication.

The `client_slug` field in the response enables the frontend to build the correct tenant-scoped redirect URL.

**Alternatives rejected:**

| Alternative | Reason for rejection |
|---|---|
| Activate returns JWT tokens (immediate login) | Duplicates `login()` token-minting logic; activate has no subdomain context; cross-tenant check skipped |
| Activate returns no `client_slug`; frontend guesses the redirect | Frontend has no way to know which subdomain the user belongs to without a DB lookup |

---

### D5 — Pre-existing bugs must be fixed before or as part of this work

> **Addendum D5-a (locked 2026-08-03, post-apply integration audit):** The RLS plumbing
> fix has an additional architectural decision: **the apply-phase implementation used an
> `engine "connect"` event with `SET LOCAL` scoped to the first transaction only.** This
> fails for pooled connections reused for subsequent requests. The locked resolution is
> **single shared engine + `Session "after_begin"` event**, not per-engine
> hook registration. Specifically:
>
> 1. **Single engine** — all service dependencies (`kernel/user/dependencies.py`,
>    `kernel/auth/dependencies.py`, `business/tenant_institution/dependencies.py`) import
>    `get_engine()` from `kernel/db.py`; no per-service `create_engine(...)` calls.
> 2. **Session-level event** — the RLS hook registers on the shared `sessionmaker` via
>    `@event.listens_for(Session, "after_begin")`, reads `_tenant_context_var`
>    at fire-time, and runs `SET LOCAL app.*` once per transaction. Pooled connections
>    reused for a later request fire the hook fresh.
> 3. **Contextvar-fresh** — the hook reads the contextvar at each new transaction's
>    creation, guaranteeing it sees the middleware's resolved `TenantContext` for the
>    current request, not a stale value from connection checkout.
> 4. **Bootstrap-safe** — when `_tenant_context_var.get()` returns `None` (CLI, migration,
>    early startup, unauthenticated flows), the hook returns without setting any
>    variables. No bypass, no raised error.
>
> **Rejected alternatives:**
>
> - Per-engine hook registration in each `dependencies.py` — reproduces the current
>   trap (new service = new way to forget the hook); also creates 4+ separate
>   connection pools to the same database.
> - `SET SESSION` (not `SET LOCAL`) on `connect` — survives connection reuse but
>   opens cross-tenant leakage if a pooled connection is shared across requests with
>   different tenant contexts.
>
> **Risk accepted:** Single shared engine increases contention on one connection pool under
> load. For Phase 1 (single-tenant-per-request, low concurrency) this is a non-issue; if
> contention appears, the right response is tuning pool size, not fragmenting engines.

**Decision:** Three production-breaking bugs sit on the activation path. They are blockers for the unified flow (both CD and institution-user activation hit them) and must be resolved:

| Bug | File | Fix |
|-----|------|-----|
| `update_user` NameError — `user_metadata` referenced but not a parameter | `supabase_client.py:252-272` | Add `user_metadata: dict \| None = None` to `SupabaseAuthClientImpl.update_user` signature |
| RLS session vars (`app.is_platform_owner`, `app.current_client_id`) never set on endpoint sessions | `middleware.py` (missing hook) | Add a SQLAlchemy `before_request` event or `Session` listener that runs `SET LOCAL app.is_platform_owner`, `SET LOCAL app.current_client_id` from the resolved `TenantContext` on every endpoint session |
| `app.current_user_id` never populated anywhere | entire runtime (missing logic) | Set `SET LOCAL app.current_user_id` in the same session hook, using `ctx.user_id` from `TenantContext` (available for authenticated requests; NULL for unauthenticated activate — which is fine because activate should operate with `app.is_platform_owner = true` or a dedicated registration bypass) |

**Rationale:** The activate endpoint, the login flow for CD, and the CD own-row SELECT/UPDATE RLS policies all depend on these session variables being set. The current production code is broken; tests mask it via `conftest.py` line 142. Resolving these bugs is a prerequisite for the unified activation flow to work in production.

---

### D6 — Replace both services with a single `UserService`; keep authentication separate

**Decision:** Replace `ClientUserService` and `IdentityUserService` with a **single `UserService`** (or `UserCreationService`) that owns all user-lifecycle behavior. Keep `AuthService` (`backend/kernel/auth/services/service.py`) as a **separate service** for login, refresh, logout, activate, OTP, and password-reset flows. The two services have distinct change rhythms and distinct concerns — user management is about user records and lifecycle, authentication is about tokens and session management.

- **`UserService`** owns: `create_user`, `update_user`, `delete_user`, `get_user`, `list_users`, `transition_lifecycle`, role assignment. Plus audit emission, cross-tenant check, invite-URL minting, and the new `StrategyResolver`.
- **`AuthService`** owns: `login`, `refresh`, `logout`, `activate`, `request_otp`, `verify_otp`, `request_password_reset`, `confirm_password_reset`, `change_password`. Plus the JWT-minting logic (PO custom HS256, CD custom HS256, institution Supabase access token).

**Rationale:** The two services have different concerns and different consumers. `UserService` is called by the user-management routes (`/api/v1/users`, `/api/v1/users/{id}`, `/api/v1/users/{id}/roles`, `/api/v1/users/{id}/transition`, `/api/v1/platform/clients/{id}/users`). `AuthService` is called by the auth routes (`/api/auth/login`, `/api/auth/refresh`, `/api/auth/activate`, `/api/auth/otp/*`, `/api/auth/password/*`). Merging them would create a god-service with two unrelated responsibility areas. Keeping them separate honors the Single Responsibility Principle.

**Alternatives rejected:**

| Alternative | Reason for rejection |
|---|---|
| Merge into one service | Mixes user-lifecycle and authentication concerns; harder to test, harder to navigate |
| Keep two services with no strategy pattern | Asymmetries between the two services (response shape, audit emission, cross-tenant check) are already documented in `docs/architecture/audit-c02-implementation-2026-08-03.md` — a strategy pattern fixes the root cause |

---

### D7 — `StrategyResolver` inside `UserService`; DTO type for create, DB lookup for others

**Decision:** `UserService` has an internal `StrategyResolver` that picks the right strategy for the operation:

- **For `create_user(ctx, dto)`:** dispatch on DTO type. `isinstance(dto, ClientUserCreateDTO)` → `CDStrategy`; `isinstance(dto, UserCreateDTO)` → `InstitutionUserStrategy`. The DTO type IS the tier discriminator. No `tier` field on the DTO.
- **For `update_user`, `delete_user`, `get_user`, `list_users`, `transition_lifecycle`:** look up the user by ID (or query filters), read the `tier` from the user record, and dispatch. The tier is sourced from the database, not from the caller.

The strategy interface is **full-symmetric** (D9 below). Both strategies implement the same methods.

**Rationale:** The DTO type encodes "this DTO is for creating a CD" or "this DTO is for creating an institution user" — the type system already provides the discriminator. For tier-agnostic operations (update, delete, list), the tier is a property of the user record, not the operation — the database is the source of truth. Adding a `tier` field to every DTO would put dispatch metadata on a data carrier, violating the principle that DTOs are transport-only.

**Long-term evolution:** The `StrategyResolver` will evolve to select strategies based on **`Organization.type`** (via `Membership`) rather than DTO type. This aligns with a DDD model where the user's relationship to the organization determines behavior, and avoids coupling business behavior to transport objects. The current DTO-type dispatch is a stepping stone toward that evolution. When `Organization` and `Membership` are introduced (likely in C-01 or a future capability), the resolver will look up the user's membership and select the strategy accordingly. The DTO-type dispatch is the initial behavior; the membership-based dispatch is the target architecture.

**Alternatives rejected:**

| Alternative | Reason for rejection |
|---|---|
| Explicit `tier` field on every DTO | Puts dispatch metadata on a data carrier; doesn't work for tier-agnostic operations |
| Strategy at route level | Routes should be thin; service owns business logic |
| Strategy at middleware level | Middleware resolves tenant context, not business behavior |
| Per-service `StrategyResolver` (one each in `IdentityUserService` and `ClientUserService`) | Defeats the point of unification; doesn't fix the asymmetries |

---

### D8 — Strategy interface is full-symmetric

**Decision:** The strategy interface defines the full contract for user lifecycle. Both `CDStrategy` and `InstitutionUserStrategy` implement every method:

- `create_user(ctx, dto) → CreateUserResponse` — DTO is strategy-specific (`ClientUserCreateDTO` for CD, `UserCreateDTO` for institution); response is unified: `{user, invite_url}`. The strategy owns: which DB table to write to (`client_user` vs `app_user`), which tier flag to stamp to Supabase (`user_metadata.user_tier`), which invite token to mint, which invite URL to build. The service's `create_user` orchestrates: dispatch to strategy, then return the unified response.
- `update_user(ctx, user_id, dto) → UserDTO` — strategy owns the row update + audit emit.
- `delete_user(ctx, user_id) → None` — strategy owns the cascade order (which related rows to delete in which order) + Supabase Auth user delete + audit emit.
- `get_user(ctx, user_id) → UserDTO | None` — strategy owns the row fetch.
- `list_users(ctx, **filters) → list[UserDTO]` — strategy owns the query (and the tier-scoped tenant filter).
- `transition_lifecycle(ctx, user_id, new_state, reason) → UserDTO` — strategy owns the state machine + lifecycle event record.

**Rationale:** A symmetric interface forces both strategies to implement the same methods. If a method is missing in one strategy, the type system catches it at instantiation. Symmetric interfaces also enable testing: a `MockStrategy` can be injected for unit tests of the service.

**Alternatives rejected:**

| Alternative | Reason for rejection |
|---|---|
| Asymmetric interface (each strategy declares only its tier-specific methods) | The asymmetries (audit missing on CD, response shape different on CD) are exactly the bug. An asymmetric interface would let those asymmetries persist |
| Strategy only for tier-specific bits (DB model + tier flag) with common code in the service | Asymmetries (audit, response shape) live in the service; the strategies only do data-write. Doesn't fix the audit-gap and response-shape bug |

---

### D9 — `LoginResponse` is a single unified model with optional tier fields

**Decision:** The `LoginResponse` (or `TokenResponse`) is a single Pydantic model with optional fields for all tier-specific data:

```python
class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    # Tier-specific optional fields
    is_platform_owner: bool | None = None
    user_tier: Literal["client_leadership", "institution"] | None = None
    client_id: uuid.UUID | None = None
```

The login response carries **all** tier-specific fields, but each is optional. PO login returns `is_platform_owner=True, user_tier=None, client_id=None`. CD login returns `is_platform_owner=False, user_tier="client_leadership", client_id=<uuid>`. Institution login returns `is_platform_owner=False, user_tier="institution", client_id=<uuid>`.

The current narrow `TokenResponse` (which strips tier fields) is replaced by this unified model.

**Rationale:** The current `TokenResponse` model filters out tier fields, so the frontend never knows which user type just logged in. The unified model ensures all tier data is visible to the frontend without requiring a separate `/me` endpoint.

---

### D10 — Bug fixes from the 2026-08-03 audit are folded into this refactor

**Decision:** The refactor implements the strategy pattern AND fixes the bugs surfaced by the 2026-08-03 audit (`docs/architecture/audit-c02-implementation-2026-08-03.md`):

| # | Bug | Fix |
|---|------|-----|
| 1 | `request_otp` NameError (signature missing `ip_address`) | Add `ip_address: str | None = None` to `AuthService.request_otp` signature; route extracts it from `http_request` |
| 2 | `TokenResponse` strips tier fields | Replaced by unified `LoginResponse` per D9 |
| 3 | `app.current_institution_id` not set in RLS hook | Add `SET LOCAL app.current_institution_id = '<ctx.institution_id>'` to the D5-a hook in `kernel/db.py` |
| 4 | Missing cross-tenant check in `_login_client_leadership` | Add it (compare `ctx.client_id` to `user_obj.client_id`) — same logic as the institution-user branch |
| 5 | Activate flow commits AFTER Supabase call → inconsistent state | Reorder: commit DB first, then call Supabase `update_user`. If Supabase fails after commit, the DB rollback is impossible — wrap in a saga or accept eventual consistency with a retry |
| 6 | `create_user` validates role AFTER Supabase user creation → two-phase inconsistency | Reorder: validate role first, then create Supabase user. If Supabase fails, the DB is already committed — same saga/retry story |
| 7 | `Migration 012` untracked in git | Commit the file: `git add backend/migrations/versions/012_app_user_institution_id_not_null.py` |
| 8 | `ClientUserService.bootstrap_invite` doesn't emit audit event | Replaced by strategy pattern — both strategies emit audit symmetrically |
| 9 | `FakeSupabaseAuth.update_user` uses merge semantics, real uses overwrite | Fix the fake to overwrite (use `=`, not `.update()`) |
| 10 | `users.py:31` permission resource name `user` vs `client_user` inconsistency | Standardize on `user` as the Casbin resource name; the tier is determined by the strategy at runtime, not the permission name |

**Rationale:** These bugs were caused by the same root cause as the asymmetries — a patched-state that didn't honor D1-D5 symmetrically. Folding them into the refactor ensures the new code is clean from day one. The alternative — fixing the bugs without the refactor — would leave the asymmetries in place and require a second round of fixes.

---

### D11 — Defer Supabase Auth user creation to activate time

**Decision:** Supabase Auth user creation is **removed from bootstrap** and **moved to activate time**. The bootstrap endpoints (`POST /api/v1/platform/clients/{id}/users` for CD, `POST /api/v1/users` for institution users) create only the DB row and mint the invite JWT. The activate endpoint (`POST /api/auth/activate`) creates the Supabase Auth user **with the password** in a single `POST /auth/v1/admin/users` call.

**Current flow (broken):**
```
Bootstrap:  POST /admin/users {email, email_confirm: true}  → ✅ works (no password)
Activate:   PUT  /admin/users/<id> {password}               → ❌ "User not allowed"
```

**New flow (D11):**
```
Bootstrap:  DB row + invite JWT only                         → no Supabase call
Activate:   POST /admin/users {id, email, password,          → ✅ works (password at creation)
            email_confirm: true, user_metadata}
```

The `SupabaseAuthClient.create_user` method gains an optional `password` parameter. The `POST /auth/v1/admin/users` endpoint accepts `password` as an optional body parameter — when provided, the user is created with that password. When omitted (as in the old bootstrap flow), the user has no password and can only authenticate via OTP/magic link.

The `update_user` method is **no longer called during activate**. It remains available for other use cases (changing password for already-active users, email changes, metadata updates) but the activate flow no longer depends on it.

**Rationale:** The Supabase Auth Admin API's `PUT /admin/users/<id>` endpoint returns "User not allowed" on our Supabase project when attempting to set a password on an admin-created user. This is a Supabase-platform constraint (possibly project-level configuration or GoTrue version behavior). The `POST /admin/users` endpoint accepts `password` at creation time, which is the supported path. Deferring Supabase creation to activate time means:

1. **No broken `update_user` dependency.** The activate flow uses `create_user` (which works) instead of `update_user` (which doesn't).
2. **Atomic password setting.** The user is created with their real password in one call — no temporary credentials, no two-step dance.
3. **No Supabase user without a password.** In the old flow, bootstrap created a Supabase user with no password — they couldn't sign in until activate set one. In the new flow, the Supabase user only exists once they have a password.

**Trade-off:** Between bootstrap and activate, the DB row exists without a matching Supabase Auth user. If someone tries to log in before activating, Supabase returns "user not found" instead of "account not active". This is acceptable because:
- The user can't log in either way (no password in old flow; no Supabase user in new flow)
- The lifecycle status in the DB is `invited` — the login endpoint checks this before calling Supabase
- The error message difference is invisible to the user (both result in "Invalid email or password")

**Alternatives rejected:**

| Alternative | Reason for rejection |
|---|---|
| Fix `update_user` by switching from SDK to raw httpx (like `create_user`) | The SDK's `update_user_by_id` may be calling a different Supabase Auth endpoint than expected; switching to raw httpx for `update_user` is speculative and may hit the same "User not allowed" error from the GoTrue server side |
| Pass password during bootstrap's `create_user` call | The password isn't known at bootstrap time — the user sets it when clicking the invite link |
| Use Supabase's invite flow (`POST /admin/generate_link` with `type: invite`) | Supabase's invite flow sends its own email and doesn't integrate with our invite JWT or lifecycle transition |
| Keep bootstrap creating Supabase user + use `update_user_raw` (raw httpx PUT) | Still depends on `PUT /admin/users/<id>` working — the same endpoint that returns "User not allowed". Adding raw httpx doesn't change the server-side rejection |

---

### D12 — `user_account` parent table for cross-tier referential integrity

**Decision:** Introduce a `user_account` table that serves as the shared identity parent for both `app_user` (institution users) and `client_user` (CD users). Both child tables reference `user_account.id` via FK. The `role_assignment.user_id` and `login_attempt.user_id` FKs point to `user_account.id` instead of `app_user.id`.

**Problem:** Two FK constraints reject CD user UUIDs:
- `role_assignment.user_id` → FK → `app_user.id` — CD users are in `client_user`, not `app_user`. CD role assignment fails.
- `login_attempt.user_id` → FK → `app_user.id` — CD login audit recording fails.

Both tables need to reference both user populations. Dropping the FKs (Option A from D11 context) loses referential integrity. A shared parent table preserves it.

**Schema:**
```
user_account (id UUID PK)
    ↑                ↑
app_user.id      client_user.id
(FK to parent)   (FK to parent)

role_assignment.user_id → FK → user_account.id
login_attempt.user_id   → FK → user_account.id
```

**Creation flow:** When creating any user (CD or institution), the strategy inserts a `user_account` row first, then inserts the child row (`app_user` or `client_user`) with the same UUID. The UUID is generated once and shared across all three tables.

**Migration strategy:**
1. Create `user_account` table
2. Backfill: INSERT INTO `user_account` SELECT id FROM `app_user` UNION SELECT id FROM `client_user`
3. Add FK on `app_user.id` → `user_account.id`
4. Add FK on `client_user.id` → `user_account.id`
5. Drop old FK on `role_assignment.user_id` → `app_user.id`
6. Add new FK on `role_assignment.user_id` → `user_account.id`
7. Drop old FK on `login_attempt.user_id` → `app_user.id`
8. Add new FK on `login_attempt.user_id` → `user_account.id`

**Rationale:**
- Preserves referential integrity at the DB level for both user types.
- `role_assignment` can now hold rows for both CDs and institution users.
- `login_attempt` can record audit events for both user types.
- No application-level orphan risk — the FK enforces existence.
- Aligns with the "one identity, many representations" pattern (a user is an account first, then specialized into CD or institution).

**Alternatives rejected:**

| Alternative | Reason for rejection |
|---|---|
| Drop FKs entirely (no parent table) | Loses referential integrity. Application bugs could create orphaned role_assignment or login_attempt rows. |
| Dual nullable FKs (user_id + client_user_id columns) | Every query needs COALESCE. Nullable columns add complexity. Doesn't scale if more user types are added. |
| Trigger-based validation (keep FK dropped, add BEFORE INSERT trigger) | Non-standard. Trigger maintenance burden. Less discoverable than FK. |
| Store CDs in `app_user` (single table) | Changes the entire two-tier architecture (D6). The CD vs institution distinction is fundamental to the data model. |

---

### D13 — UserProfile: self-service + admin permission + cross-tier FK fix

**Decision:** Any authenticated user can create, read, and update their own profile (self-service via `owner_id` check). Admin/CD/institution_admin can manage any profile via a new `user_profile.admin` permission. The `UserProfile.user_id` FK is changed from `app_user.id` to `user_account.id` (same as D12) so CD users can also have profiles.

**Problem:**
1. `UserProfile.user_id` FK → `app_user.id` — CD users in `client_user` can't have profiles
2. No role has `user_profile.create` — the permission exists but isn't assigned
3. No ownership check on profile read/update — any user with permission can access any profile
4. Teacher/Staff/Student/Parent don't have `user_profile.update` — can't update own profile

**Solution:** Use a two-tier permission model instead of a complex ownership check:
- **Self-service:** `_check_impl` Stage 3 checks `owner_id == ctx.user_id` → return immediately. No Casbin check needed. Any user can manage their own profile.
- **Admin management:** New `user_profile.admin` permission for Admin/CD/institution_admin. Profile routes check `user_profile.admin` for non-self access. Casbin enforces scope (tenant/institution).
- **No ownership check (Stage 5):** Removed from `_check_impl`. Casbin + self-access handle all cases.

**Permission matrix after fix:**

| Role | self-service (any action) | user_profile.admin | Scope |
|---|---|---|---|
| Admin | ✅ (Stage 3 bypass) | ✅ | institution |
| client_director | ✅ (Stage 3 bypass) | ✅ | tenant |
| institution_admin | ✅ (Stage 3 bypass) | ✅ | institution |
| Teacher | ✅ (Stage 3 bypass) | ❌ | — |
| Staff | ✅ (Stage 3 bypass) | ❌ | — |
| Student | ✅ (Stage 3 bypass) | ❌ | — |
| Parent | ✅ (Stage 3 bypass) | ❌ | — |

**Authorization flow:**
```
Stage 1: Platform Owner bypass (PO can do anything)
Stage 2: Role validation (must have roles)
Stage 3: Self-access bypass (owner_id == ctx.user_id → return)
Stage 4: Casbin check (user_profile.admin for non-self access)
(Stage 5: REMOVED — no longer needed)
```

**Rationale:**
- Profiles are personal data (DOB, gender, blood group). Users should always manage their own.
- Admins need to manage profiles on behalf of users (e.g., during bulk import).
- The `user_profile.admin` permission cleanly separates self-service from admin management.
- Removing Stage 5 (ownership check) simplifies `_check_impl` and eliminates the broken admin bypass logic.

**Alternatives rejected:**

| Alternative | Reason for rejection |
|---|---|
| Keep ownership check with ctx IDs (current fix) | Both Teacher and Admin have same permission at same scope — Casbin can't distinguish them |
| Hardcode admin role names in bypass | Unmaintainable, doesn't scale |
| Use different scopes for admin vs non-admin | Overcomplicates the permission model |

---

## 3. Consequences

### Positive

- **One mental model for all users.** Creation → invite → activate → login. No special cases, no Supabase Admin API workarounds.
- **`service_role` key never reaches the browser.** The journey-flow workaround is retired.
- **Single token-minting path.** `login()` handles all user types. No risk of activate and login diverging.
- **Config-driven invite URL.** Works across environments without code changes.
- **Cleaner test surface.** One activation flow to test, not two.
- **Role assignment at creation.** One API call instead of two for the common case.

### Negative

- `POST /api/v1/users` changes its response contract — now returns `{user, invite_url}` instead of just `UserDTO`. This is a breaking change for any client that depends on the current response shape.
- The `pending` lifecycle state for institution users becomes unused in the normal flow (still available for manual transitions).
- The RLS bugs need fixing — these touches middleware and session plumbing, which affects every request not just activation.

---

## 4. Model

```
┌────────────────────────────────────────────────────────────┐
│                     USER CREATION (Bootstrap)              │
│                                                            │
│  PO creates CD:                                            │
│    POST /api/v1/platform/clients/{id}/users                │
│    → client_user row (invited)                             │
│    → invite JWT                                            │
│    → returns {user_id, invite_url}                         │
│    (NO Supabase Auth call — D11)                           │
│                                                            │
│  CD creates institution user:                              │
│    POST /api/v1/users                                      │
│    {email, name, user_category_id, institution_id,         │
│     role_id?}                                              │
│    → app_user row (invited)                                │
│    → role_assignment row (if role_id provided)             │
│    → invite JWT                                            │
│    → returns {user, invite_url}                            │
│    (NO Supabase Auth call — D11)                           │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│                     USER ACTIVATION                        │
│                                                            │
│  User clicks invite link:                                  │
│    GET {app.activationBaseUrl}/activate?token=<jwt>        │
│                                                            │
│  User sets password:                                       │
│    POST /api/auth/activate {invite_token, password}        │
│    → verify invite JWT → extract user_id                   │
│    → elevated session: look up user identity (tier, slug)  │
│    → normal session: transition lifecycle invited → active │
│    → COMMIT DB FIRST (saga pattern)                        │
│    → Supabase create_user WITH password (D11)              │
│    → emit audit (actor = user_id from token)               │
│    → returns {message, user_id, user_tier, client_slug}    │
│                                                            │
│  Frontend redirects to:                                    │
│    {client_slug}.<host>/login                              │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│                     USER LOGIN                             │
│                                                            │
│  User enters email + password:                             │
│    POST /api/auth/login {email, password}                  │
│    Host: {client_slug}.<host>                              │
│                                                            │
│  login() branches per user_tier:                           │
│    platform_owner    → custom HS256 JWT                    │
│    client_leadership → custom HS256 JWT (client_id, role)  │
│    institution       → Supabase access_token               │
└────────────────────────────────────────────────────────────┘
```

---

## 5. Constraints

- **RLS must be functional.** D5 bugs must be fixed before the unified activation flow can work in production. Tests that mask the gap (`conftest.py` line 142) must be updated to reflect the new session-var plumbing.
- **Breaking change on `POST /api/v1/users` response.** The response shape changes from `UserDTO` to a combined object. Any downstream consumers (currently only the journey-flow HTML) must be updated.
- **Invite JWT secret must match.** The same `APP_INVITE_JWT_SECRET` is used for both CD and institution-user invite tokens. The middleware already handles this distinction (line ~210 of `middleware.py`).
- **Config key migration required.** `app.activationBaseUrl` must be seeded via a new Alembic migration per AGENTS.md §8.

---

## 6. Alternatives Considered

| Alternative | Reason for Rejection |
|---|---|
| Keep two separate activation paths (CD via invite JWT, institution users via Admin-set password) | Two code paths; no self-service for institution users; Supabase Admin bypass continues |
| Institution users activate via Supabase email-confirmation webhook + lifecycle hook | Requires new webhook infra; Supabase's email-confirmation doesn't trigger our lifecycle transition |
| Return JWT tokens from `/api/auth/activate` (immediate login) | Duplicates `login()` token minting; activate has no subdomain context; cross-tenant check skipped |
| Use Supabase's built-in invite/password-reset flow instead of our custom invite JWT | Supabase's flow only sends email; it doesn't transition our lifecycle states; doesn't integrate with C-08 activation config |
| Keep role assignment as a separate call (no `role_id` on creation DTO) | Extra round trip; the creator knows the role at creation time |

---

## 7. Future Evolution

- **Bulk user import / CSV upload.** The `role_id` field remains optional to support bulk imports where role assignment may be deferred.
- **Email delivery of invites.** C-09 Notification Framework will eventually handle sending activation emails. The current flow (API returns `invite_url`; creator forwards out-of-band) is Phase 1 only.
- **`pending` lifecycle state.** If a use case emerges that requires an explicit staging step between invited and active (e.g., document verification), the `pending` state is available via `POST /api/v1/users/{id}/transition` and the activate endpoint can be updated to support `invited → pending`.
- **Activate returns tokens.** If a future UX review strongly prefers immediate login after activation, this decision (D4) can be revisited. The cost is duplicating login token-minting logic in activate.
- **Invite token expiry per tenant.** Currently a single `auth.inviteExpiryDays` config key. If different clients want different expiry windows, this can evolve to a client-scoped override in C-08.
