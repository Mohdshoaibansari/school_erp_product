# Design — C-02 User Creation & Activation

> **Change ID:** `add-c02-user-creation-activation`
> **Source:** `docs/architecture/adr-c02-identity-user-management-implementation.md` (D1–D5)
> **Specs:** `specs/identity-user-management/spec.md`, `specs/authentication/spec.md`, `specs/configuration-framework/spec.md`, `specs/auth-infrastructure/spec.md`

---

## 1. Approach

### 1.1 Unified invite JWT minting

Every user-creation path mints the same kind of invite JWT using the existing `mint_invite_token(user_id, email)` function from `kernel/auth/services/invite_token.py`. No new token format, no new signing key. The `auth.inviteExpiryDays` config key (already seeded) controls expiry for all invite tokens — CD and institution users alike.

```
mint_invite_token(user_id, email)
  → JWT with {sub, email, exp, iat, iss="school-erp/invite"}
  → signed HS256 with APP_INVITE_JWT_SECRET
  → URL = {config.get("app.activationBaseUrl")}/activate?token={jwt}
```

The `POST /api/v1/users` service layer (`kernel/user/services/service.py`) gains two lines of logic:
1. After `app_user` row is inserted: call `mint_invite_token(user_id, email)` → get `invite_jwt`
2. Build `invite_url = f"{config.get('app.activationBaseUrl')}/activate?token={invite_jwt}"`
3. Return `{user: UserDTO, invite_url: invite_url}` instead of just `UserDTO`

The PO bootstrap path (`client_user_service.py`) already mints invite tokens. The only change there is replacing the hardcoded `frontend_url = "http://127.0.0.1:8000"` with `config.get("app.activationBaseUrl")`.

### 1.2 Single activate endpoint for both tiers

`POST /api/auth/activate` already handles both `client_user` and `app_user` (lines 355–430 of `service.py`). The changes are:

| Aspect | Current | Target |
|--------|---------|--------|
| Response | `{message, user_id}` | `{message, user_id, user_tier, client_slug}` |
| client_slug derivation | Not computed | Look up via `client_user.client.slug` or `app_user.institution.client.slug` |
| user_tier | Not returned | `"client_leadership"` or `"institution"` |
| Tokens | Not returned (already correct) | Unchanged — stays no-token per D4 |

The `client_slug` is resolved inside the activate service method after the user is identified. For `client_user`: join to `client` table on `client_id`. For `app_user`: join through `institution` to `client`. This is a read-only lookup added to the existing activation transaction.

### 1.3 Config-driven invite URL

Replace the single hardcoded line `frontend_url = "http://127.0.0.1:8000"` in `client_user_service.py:91` with:

```python
from kernel.config.resolver import config
frontend_url = config.get("app.activationBaseUrl") or "http://127.0.0.1:8000"
```

The new `app.activationBaseUrl` config key is seeded via a new Alembic migration with default `"http://127.0.0.1:8000"`.

### 1.4 Three D5 bug fixes (prerequisites)

**Bug 1 — `user_metadata` NameError:** Add `user_metadata: dict | None = None` to `SupabaseAuthClientImpl.update_user()` signature at `supabase_client.py:256`. The body already handles it; only the signature is missing.

**Bug 2 — RLS session-var hook:** Add a SQLAlchemy `event.listen()` hook (or FastAPI middleware) that, after `TenantContext` is resolved, executes `SET LOCAL` for `app.is_platform_owner`, `app.current_client_id`, and `app.current_user_id` on the request's database session. The hook fires once per request, after tenant resolution, before the endpoint handler.

**Bug 3 — `app.current_user_id`:** Populated in the same hook, sourced from `ctx.user_id` (available for authenticated requests; `None` for unauthenticated). This makes RLS policies like `client_user_cd_select_own` functional.

---

## 2. Architecture Flow

```
┌───────────────────────────────────┐
│         USER CREATION             │
│                                   │
│  Platform Owner                   │
│    POST /platform/clients/{id}/   │
│         users                     │
│    → client_user (invited)        │
│    → mint invite JWT              │
│    → config.get("app.activation   │
│         BaseUrl") + token         │
│    → {user_id, invite_url}        │
│                                   │
│  Client Director                  │
│    POST /api/v1/users             │
│    {email, name, category,        │
│     institution_id, role_id?}     │
│    → app_user (invited)           │
│    → role_assignment (if role_id) │
│    → mint invite JWT              │
│    → config.get("app.activation   │
│         BaseUrl") + token         │
│    → {user, invite_url}           │
└──────────────┬────────────────────┘
               │
               ▼
┌───────────────────────────────────┐
│         USER ACTIVATION           │
│                                   │
│  New User                         │
│    GET /activate?token=<jwt>      │
│    → Enter password               │
│    POST /api/auth/activate        │
│    {invite_token, password}       │
│                                   │
│  Backend                          │
│    → verify_invite_token()        │
│    → lookup app_user by UUID      │
│    → fallback: lookup client_user │
│    → 400 if already active        │
│    → Supabase update_user(        │
│        password, email_confirm)   │
│    → transition invited→active    │
│    → resolve client_slug          │
│    → {message, user_id,           │
│        user_tier, client_slug}    │
│                                   │
│  Frontend                         │
│    → redirect to                   │
│      {client_slug}.host/login     │
└──────────────┬────────────────────┘
               │
               ▼
┌───────────────────────────────────┐
│         USER LOGIN                │
│                                   │
│  User                             │
│    POST /api/auth/login           │
│    {email, password}              │
│    Host: greenwood.host           │
│                                   │
│  login() branches:                │
│    platform_owner    → HS256 JWT  │
│    client_leadership → HS256 JWT  │
│    institution       → Supabase   │
│                        access     │
│                        token      │
└───────────────────────────────────┘
```

---

## 3. Tradeoffs

| Tradeoff | Choice | Rationale |
|----------|--------|-----------|
| Invite URL in API response vs. separate endpoint | Included in response | Simplest Phase 1 path; email will be added by C-09 later without changing activation |
| `client_slug` lookup in activate vs. frontend derives it | Backend returns it | Frontend has no way to know the slug without a DB call; activate already has the user row |
| No JWT tokens from activate | Correct per D4 | Keeps `login()` as single token-minting path; activate runs without subdomain context |
| `pending` state retained vs. removed | Retained on state machine | Minimal change; `pending` may be useful for future manual admin flows; activate bypasses it |
| RLS hook as SQLAlchemy event vs. FastAPI middleware | SQLAlchemy event | `SET LOCAL` is per-transaction; SQLAlchemy events scope it correctly; middleware approach would require extracting the session per-request |
| `user_metadata` fix: just add the parameter | Yes | Minimal; the body already works; only the signature is missing |

---

## 4. Breaking Changes

| Change | Affects | Mitigation |
|--------|---------|------------|
| `POST /api/v1/users` response shape → `{user, invite_url}` | Journey flows (`02_client_director.html`) | Update HTML to handle new shape |
| `POST /api/auth/activate` response adds `user_tier`, `client_slug` | Journey flows (`01_platform_owner.html`, `09_platform_bootstrap.html`) | Update step 7 in both files |
| Supabase Admin workaround removed | Journey flows (`02_client_director.html`, `09_platform_bootstrap.html`) | Replace with backend transition endpoint calls |
| RLS session-var hook affects all requests | All endpoints | Hook is additive (`SET LOCAL`); comprehensive test coverage; thorough manual regression |

---

## 5. Migration

One new Alembic migration seeds the `app.activationBaseUrl` config key:

```sql
INSERT INTO configuration_key (key, type, default_value, category, module, description, created_at, updated_at)
VALUES (
  'app.activationBaseUrl',
  'string',
  '"http://127.0.0.1:8000"',
  'Business Rules',
  'app',
  'Base URL used to construct activation/invite links sent to new users.',
  NOW(),
  NOW()
);
```
