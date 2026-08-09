# C-02 Implementation Audit — User & Identity Management

> **Status:** Audit findings (input to fix decisions; no fixes applied yet)
> **Audited:** 2026-08-03
> **Scope:** All user & identity management code touched by the C-02 User Creation & Activation change, plus the pre-existing surface that surrounds it
> **Verdict:** **PATCHED, not designed.** Multiple asymmetries between the two user tiers, hardcoded values that should be config keys, response_model drift, log inconsistency, and a small number of P1 runtime breakages remain. See fix recommendations table at the end — none of these are 1-day jobs but most are small.

This audit is a read-only analysis. Every observation cites file:line. No files were modified.

---

## 1. Two-tier asymmetry: `client_user` vs `app_user`

The platform has two user populations stored in separate tables (`client_user` and `app_user`) per the ADR D1/D10. The implementation treats them differently in several places that the ADR does not call out as different.

| Surface | `app_user` path | `client_user` path | Severity |
|---|---|---|---|
| **Service class** | `IdentityUserService` (`backend/kernel/user/services/service.py`) | `ClientUserService` (`backend/kernel/user/services/client_user_service.py`) | OK — two services is consistent with two repositories |
| **Construction** | DI'd via `kernel/user/dependencies.py: get_identity_user_service` | Not in the DI graph at all — instantiated manually inside `client_users.py` route | **MAJOR** — if the rest of the kernel uses one DI pattern, this should too. Manual instantiation here means tests cannot substitute the supabase_auth or config_resolver via `app.dependency_overrides` |
| **`create_user` response shape** | `{"user": UserDTO, "invite_url": str}` (D1) | `{"user_id": str, "email": str, "invite_url": str, "client_id": str}` (inconsistent — `email` and `client_id` are top-level but `user_id` is a string, not nested under `user`) | **MAJOR** — the PO bootstrap endpoint returns a different shape than the CD one. The C-02 ADR says "both modes produce identical Client structure" but the API responses differ. Frontends consuming both must branch. |
| **Invite URL minting** | `IdentityUserService.create_user` lines 132-140: `mint_invite_token(result.id, result.email)` + `config.get("app.activationBaseUrl")` | `ClientUserService.bootstrap_invite` lines 87-92: same pattern (D3) | OK — symmetric |
| **Tier flag stamped to Supabase** | `IdentityUserService.create_user` line 120-122: `user_metadata={"user_tier": "institution"}` | `ClientUserService.bootstrap_invite` lines 55-60: `user_metadata={"user_tier": "client_leadership"}` | OK — symmetric (after the Fix #1 uid= → positional bug) |
| **Audit emit** | `action="user_created"` with `payload={user_id, email, name}` | **MISSING** — bootstrap_invite never calls `self._audit.emit(...)` | **MAJOR** — CD creation skips the audit. Per AGENTS.md and the C-11 pattern, every state change emits an audit event |
| **Login flow** | `AuthService.login` (lines 142-200): `session.get(User, user_id)` → app_user lookup → Supabase access_token | `AuthService._login_client_leadership` (lines 215-280): `session.get(ClientUser, user_id)` → client_user lookup → mints **custom HS256 JWT** with `{sub, user_tier, client_id, role_id}` | OK in design but **MAJOR** in consequence: the CD JWT and the institution-user Supabase JWT are different token types. Any consumer that decodes the JWT to read `client_id` finds it on the CD JWT but NOT on the Supabase JWT (CD's `client_id` lives in the JWT payload; institution user's `client_id` lives in a separate `app_user` DB row). The activate flow works around this with `user_tier` routing in `login()` |
| **Cross-tenant check** | `AuthService.login` lines 178-186: `if ctx.client_id and user_dto.client_id != ctx.client_id and "platform_owner" not in (ctx.roles or []): raise AuthError(...)` | **MISSING** — `_login_client_leadership` never checks `ctx.client_id` against `user_obj.client_id`. A CD from client A can log in from client B's subdomain if they know the credentials | **CRITICAL** — this is a tenant-isolation bug introduced when `_login_client_leadership` was added. The CD bootstrap PRD D3/D4 was about client ownership, and the missing cross-tenant check undoes it. |

**Drift severity: CRITICAL (cross-tenant bug) + MAJOR (response shape, audit, DI).** The two tiers are not symmetric in audit, in response shape, or in tenant-isolation enforcement.

---

## 2. Hardcoded values that should be config keys (AGENTS.md §8 violation)

| File:line | Value | Should be |
|---|---|---|
| `backend/kernel/auth/services/service.py:135` | `from jose import jwt; jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "test-secret-for-c01")` | Already uses env var, but the default `"test-secret-for-c01"` is a leak risk in production. Should require explicit configuration or fail-fast if missing. |
| `backend/kernel/auth/services/service.py:241` | Same pattern repeated in `_login_client_leadership` | Same — duplicated, same risk |
| `backend/kernel/auth/services/service.py:280` (the `_login_client_leadership` login JWT) | Same env-var pattern | Same |
| `backend/kernel/user/services/client_user_service.py:96` | `frontend_url = config.get("app.activationBaseUrl") or "http://127.0.0.1:8000"` | OK — the config key is the right pattern. The fallback is fine for dev. **This is what the rest of the code should look like.** |

**Note:** The auth service has THREE places that reach into `os.environ.get("SUPABASE_JWT_SECRET", ...)` to mint custom HS256 JWTs. Per AGENTS.md §8, this should be a config key (`auth.jwtSecret` or similar) seeded by a migration. The hardcoded default is also a security concern.

---

## 3. `response_model` leakage

| Route | Declared model | Service returns | What's lost |
|---|---|---|---|
| `auth.py:60` `POST /login` | `TokenResponse` = `{access_token, refresh_token, token_type, expires_in}` | PO returns `{is_platform_owner: True}`; CD returns `{user_tier, client_id}` | Frontend never sees the tier flag. To know if a user is PO/CD/institution, frontend would need a separate `/me` endpoint |
| `auth.py:97` `POST /refresh` | `TokenResponse` | Returns just the token pair | OK |
| `auth.py:135` `POST /activate` | `ActivateResponse` (proper) | `{message, user_id, user_tier, client_slug}` | OK |
| `users.py:34` `POST /users` | `UserCreateResponseDTO` | `{user, invite_url}` | OK |
| `users.py:48` `GET /users` | `list[UserDTO]` | Same | OK |
| `users.py:65` `GET /users/{id}` | `UserDTO` | Same | OK |
| `users.py:80` `PATCH /users/{id}` | `UserDTO` | Service returns UserDTO via `await svc.update_user(ctx, user_id, dto)` — let me verify; if `update_user` returns the new shape, OK | **OK (verify)** |
| `users.py:103` `DELETE /users/{id}` | None (204) | OK |
| `users.py:124` `POST /users/{id}/transition` | `UserDTO` | Returns UserDTO | OK |
| `client_users.py:39` `POST /platform/clients/{id}/users` | `dict` (no Pydantic) | Returns `{user_id, email, invite_url, client_id}` | **MINOR** — `response_model=dict` provides no validation. Per the user's concern about "not aligned with existing coding," C-01 routes declare Pydantic response models; the PO bootstrap route should too |

**Severity: MAJOR for /login (the tier flag is dropped). MINOR for the PO bootstrap route (no response_model).**

---

## 4. Log format inconsistency

The `kernel/auth/services/service.py` file has a mix of log patterns. A reviewer looking for one log line per operation cannot find them:

| Method | Log line |
|---|---|
| `login` (line 71) | `logger.info("[AUTH] Login attempt: email=%s client_id=%s ip=%s", email, ctx.client_id, ip_address)` — has ip, has client_id |
| `login` (line 133) | `logger.info("[AUTH] Platform owner login success: user_id=%s email=%s", user_id, email)` — has user_id, no ip |
| `login` (line 196) | `logger.info("[AUTH] Login success: user_id=%s email=%s", user_id, email)` — no ip, no client_id |
| `refresh` (line 284) | `logger.info("[AUTH] Token refresh attempt: user=%s ip=%s", ctx.user_id, ip_address)` — uses `ctx.user_id` (may be None) |
| `logout` (line 305) | `logger.info("[AUTH] Logout attempt: user=%s ip=%s", ctx.user_id, ip_address)` |
| `activate` (line 351) | `logger.info("[AUTH] Activate attempt: invite_token=%s...", invite_token[:20])` — does NOT log client_id, ip, user_agent |
| `request_otp` (line 466) | `logger.info("[AUTH] OTP request: email=%s ip=%s", email, ip_address)` — **NameError** (signature has no ip_address) |
| `_login_client_leadership` (line 279) | `logger.info("[AUTH] CD login success: user_id=%s client_id=%s", user_id, user_obj.client_id)` — no ip, no user_agent |

**Severity: MINOR (consistency) but the `request_otp` line is CRITICAL (P1 runtime break).** The `request_otp` P1 was already flagged. The other log inconsistencies are readability/maintainability concerns.

---

## 5. `ip_address` / `user_agent` propagation

The pattern is:
- Route handler extracts `ip_address` and `user_agent` from `http_request`
- Passes them to the service method
- Service method receives them as keyword-only args
- Service logs with them, records them in `login_attempt`

`request_otp` is the **only** method that:
1. Does NOT receive `ip_address` / `user_agent` from the route (the route doesn't extract them)
2. The service method signature doesn't declare them
3. The log line references `ip_address` → NameError on every call

**Severity: CRITICAL for `request_otp` (P1 runtime break) + MINOR for the broader pattern.**

---

## 6. Transaction boundary integrity

### Activate flow (lines 345-450 of `service.py`)

```python
await self._supabase.update_user(user_id, password=password, email_confirm=True)  # external call
# ... lifecycle transition ...
session.commit()
```

If `session.commit()` fails after Supabase update succeeded, the Supabase user has a password but the DB row still says `invited`. On retry, the activate endpoint checks `if target_lifecycle == "active": raise AuthError(...)` and refuses — but the Supabase user already has a password set. User can login with that password but the DB says they aren't active. **Inconsistent state.**

The proper pattern is: validate everything, commit, then call Supabase — or wrap in a saga. The current code does the Supabase call first, then commits. If the commit fails, the Supabase state is ahead of the DB state.

**Severity: MAJOR. This is a real consistency bug.**

### `IdentityUserService.create_user` (lines 87-148)

```python
result = self._user_repo.create(session, ctx, dto)  # SQL INSERT app_user
if dto.role_id is not None:
    # role_assignment INSERT in same session
if self._supabase is not None:
    try:
        await self._supabase.create_user(result.id, result.email)
        await self._supabase.update_user(result.id, user_metadata={"user_tier": "institution"})
    except SupabaseAuthError:
        session.rollback()
        raise
# mint invite JWT, build URL
session.commit()
```

If the role_assignment INSERT fails (invalid role), the Supabase user has already been created. **Two-phase commit inconsistency.** Should be: validate role BEFORE creating Supabase user.

**Severity: MAJOR.**

---

## 7. RLS plumbing gaps

### `app.current_institution_id` not set in the hook

The D5-a addendum locked the fix for RLS session vars. The implementation in `db.py` sets `app.is_platform_owner`, `app.current_client_id`, `app.current_user_id` — but **not** `app.current_institution_id`.

The RLS policies in migration 009 (`current_institution_id()` function, used in 4 places at lines 139, 156, 173, 184) read `app.current_institution_id`. The `TenantContext` already has `institution_id`. The hook just doesn't write it.

**Consequence:** Institution-scoped config reads (e.g., a config value with `scope_type='institution', scope_id=<some_institution>`) — the RLS check `OR institution_id = current_institution_id()` evaluates to `OR institution_id = NULL` → `OR FALSE`. A user in institution A trying to read institution A's config may fail to see it (depending on the other OR branches).

**Severity: P1 (silent RLS misbehavior).** Already flagged in the 2026-08-03 review.

### RLS hook for unauthenticated flows

The activate endpoint (`/api/auth/activate`) is unauthenticated. The middleware sets a subdomain-only `TenantContext` (no user_id, no client_id if no subdomain). When the activate endpoint's service code opens its own session, the hook fires and reads `_tenant_context_var.get()` — which may have `client_id=None` (no subdomain) or may have the subdomain-resolved `client_id`. The hook then sets `app.current_client_id` to NULL.

This means the activate endpoint's session runs with `app.is_platform_owner=false, app.current_client_id=NULL`. The `client_user_cd_select_own` policy requires `id = current_setting('app.current_user_id')::uuid` — also NULL. The policy's OR-clause `NULLIF(current_setting('app.is_platform_owner', true), '') = 'true'` evaluates to NULL ≠ 'true' → no rows visible.

**Wait — then how did the activate flow work when we tested it?** The answer: it didn't. The integration audit's Find #1 (uid= TypeError) and Find #2 (user_metadata) were the visible failures. The silent RLS misbehavior was the deeper issue. The user reported the activate flow was failing — this is why.

**Severity: P1.** The D5-a fix is incomplete without `app.current_institution_id` AND without a way for unauthenticated flows (activate, OTP) to set the RLS variables. Either:
1. The activate endpoint's session must run as platform owner (`app.is_platform_owner = 'true'`) — but this would bypass ALL RLS, including `client_user_platform_owner_all`'s intended constraint
2. The activate endpoint opens a short-lived privileged session just for the user lookup, similar to the middleware's subdomain resolution

**Recommended approach:** Option 2. The activate service should do its user lookup in a separate session that sets `app.is_platform_owner = 'true'` (matching the middleware's existing pattern for subdomain resolution), then transitions to a normal session for the commit. This matches the pattern already used in `middleware.py:152-162` and `middleware.py:305-310`.

---

## 8. `TenantContext` completeness

The `TenantContext` dataclass has: `client_id, institution_id, user_id, is_platform_owner, user_tier, roles`. All six are needed for various code paths. The middleware sets all six (when present in the JWT or DB fallback). The RLS hook consumes four of them. **Missing:** the hook should also set `app.current_institution_id` from `ctx.institution_id`. **One-line fix.**

---

## 9. DTO purity

### `UserCreateDTO` vs `UserCreateResponseDTO`

- `UserCreateDTO` (request): `email, name, user_category_id, institution_id, role_id` — clean. `role_id` is optional.
- `UserCreateResponseDTO` (response): `{user: UserDTO, invite_url: str}` — clean separation from request.

**OK.**

### `UserUpdateDTO` vs `UserDTO`

- `UserUpdateDTO` (request): `name?, email?, lifecycle_status?` — clean
- `UserDTO` (response): `id, client_id, institution_id, email, name, user_category_id, lifecycle_status, created_at, updated_at` — clean

**OK.** The fact that `UserUpdateDTO.lifecycle_status` is mutable is intentional (used by the activate endpoint) but the docstring should be clearer about this.

### `ClientUserCreateDTO`, `ClientUserUpdateDTO`, `ClientUserTransitionDTO`, `ClientUserDTO`

**Need to verify** — these are in `dtos.py` but I haven't fully read them. From the client_users.py route, the bootstrap endpoint returns `dict` (no response_model) — so the response is untyped.

**Severity: MINOR (PO bootstrap route returns untyped dict).**

---

## 10. Casbin policy consistency

The casbin model uses `{sub: {role, client_id, institution_id}, obj: {name, client_id, institution_id}}`. The `require_permission` dependency in `kernel/authz/dependencies.py` builds both sub and obj from `TenantContext` (lines 95-115).

**The authz dependency correctly consumes `ctx.institution_id` for both sub and obj.** This is consistent with the C-01 ADR D11 matrix.

The `client_director` role in `business/tenant_institution/policies.py:32` is the role string. This is consistent with the kernel config bypass logic in `configuration_service.py:291` and `values.py:91` which both check for `"client_director" in (ctx.roles or [])`. **OK.**

But — `roles` on `TenantContext` is `Sequence[str]`. The casbin dep picks `roles[0]` as the sub role. If a user has multiple roles (e.g., `["client_director", "Admin"]`), only the first is used. This is a casbin design choice (sub.role is a single value in the model), not a bug.

---

## 11. `FakeSupabaseAuth` vs real `SupabaseAuthClient` consistency

Comparing the two:

| Method | `SupabaseAuthClient` Protocol | `SupabaseAuthClientImpl` | `FakeSupabaseAuth` |
|---|---|---|---|
| `create_user(user_id, email) → dict` | ✓ | ✓ | ✓ |
| `sign_in_with_password(email, password) → dict` | ✓ | ✓ returns `{access_token, refresh_token, user: {id, email, user_metadata}}` | ✓ returns `{access_token, refresh_token, user: {id, email, user_metadata}}` (after Fix #2) |
| `sign_in_with_otp(email) → dict` | ✓ | ✓ | ✓ |
| `verify_otp(email, token, type='email') → dict` | ✓ | ✓ | ✓ |
| `reset_password_for_email(email, redirect_to) → dict` | ✓ | ✓ | ✓ |
| `update_user(user_id, *, password, email, email_confirm, user_metadata) → dict` | ✓ has `user_metadata` | ✓ has `user_metadata` (after Fix #1) | ✓ has `user_metadata` (after Fix #2) |
| `sign_out(user_id, scope='global') → None` | ✓ | ✓ | ✓ |
| `delete_user(user_id) → None` | ✓ | ✓ | ✓ |
| `refresh_token(refresh_token) → dict` | ✓ | ✓ | ✓ |
| `revoke_refresh_token(refresh_token) → None` | ✓ no-op | ✓ no-op | ✓ no-op |

After the audit fixes (#1, #2), the three are now in sync. **OK.**

**But:** the `FakeSupabaseAuth.update_user` body at line 168-169:
```python
if user_metadata is not None:
    user["user_metadata"].update(user_metadata)
```

This does `dict.update()` (merges). The real `SupabaseAuthClientImpl.update_user` line 271-272:
```python
if user_metadata is not None:
    update_data["user_metadata"] = user_metadata
```

This does `=` (overwrites). **Behavior divergence on update semantics.** For a `user_metadata={"user_tier": "institution"}` call, both produce the same result (the key doesn't exist yet). But for a subsequent call passing `user_metadata={"other_key": "x"}`, the fake would preserve the old `user_tier` while the real impl would wipe it. **Subtle test/prod divergence.**

---

## 12. The `request_otp` P1 (already known)

The `request_otp` method at `service.py:457-470` references `ip_address` in the log line but doesn't declare it. Every call raises `NameError` before reaching Supabase.

**Severity: P1.** Fix: add `ip_address: str | None = None` to the signature, pass it from the route.

---

## 13. `TokenResponse` on `/login` strips tier flag (already known)

The `login` service returns `is_platform_owner: True` for PO and `user_tier, client_id` for CD. The route's `response_model=TokenResponse` filters these out. **Severity: P1 contract bug.**

---

## 14. Migration 012 untracked in git (already known)

The file `backend/migrations/versions/012_app_user_institution_id_not_null.py` exists on disk but is not committed to git. **Severity: P1 if shipping, non-issue if local.**

---

## 15. Other minor items

| File:line | Issue |
|---|---|
| `users.py:31` | `_authz: None = Depends(require_permission("user", "create"))` — uses `user` not `institution_user` as the resource. Inconsistent with `client_users.py:44` which uses `client_user` (via the `bootstrap_client_director` route). The Casbin `require_permission` resource name should be consistent. |
| `client_users.py:44` | `bootstrap_client_director` route uses `response_model=dict` (not a Pydantic model). Per C-01 patterns, this should be a typed response. |
| `service.py:19` | `from datetime import datetime, timezone` — uses `datetime.now(timezone.utc)` in three places. Standard. **OK.** |
| `service.py:134` | PO JWT comment says "Supabase's JWT doesn't carry this claim, so we issue our own" — but Supabase Auth DOES support custom claims via `app_metadata` or `user_metadata`. The CD login mints a custom JWT because `user_tier` is in `user_metadata` and the activate flow needs it. This is a design choice, not a bug. |
| `service.py:101` | `user_metadata = supabase_user.get("user_metadata") or {}` — handles missing metadata. **OK.** |
| `configuration_service.py:291` | `if "client_director" in (actor.roles or [])` — string match against `ctx.roles`. Works but fragile (typos break silently). Consider an enum or constant. |
| `kernel/tenant_context.py` | `dataclass(frozen=True)` — **OK**, immutable. |
| `kernel/tenant_context.py:55` | `is_platform_owner: bool = False` — default `False`. Anyone setting `TenantContext` manually and forgetting to set this field gets platform-owner bypass denied. **OK by design.** |

---

## Summary: P1 issues to fix before archive

| # | Issue | File:line | Severity |
|---|-------|-----------|----------|
| 1 | `request_otp` NameError | `service.py:457-470` | P1 |
| 2 | `TokenResponse` strips tier flag from `/login` | `auth.py:30-34` + `service.py:136, 279` | P1 |
| 3 | `app.current_institution_id` not set in RLS hook | `db.py:50-66` | P1 |
| 4 | `_login_client_leadership` missing cross-tenant check | `service.py:215-280` | CRITICAL |
| 5 | Activate flow commits AFTER external Supabase call | `service.py:394-403` | MAJOR |
| 6 | `create_user` role-validation happens AFTER Supabase user creation | `service.py:88-122` | MAJOR |
| 7 | Migration 012 untracked in git | filesystem | P1 if shipping |
| 8 | `ClientUserService.bootstrap_invite` doesn't emit audit event | `client_user_service.py:46-100` | MAJOR |
| 9 | `FakeSupabaseAuth.update_user` uses merge semantics, real uses overwrite | `fake_supabase_auth.py:168-169` | MINOR |
| 10 | `users.py:31` permission resource name `user` vs `client_user` inconsistency | `users.py:31`, `client_users.py` | MINOR |

## Recommended fix order

1. **Add `app.current_institution_id` to the RLS hook** (P1, 1 line)
2. **Fix `request_otp` signature** (P1, add `ip_address: str | None = None`)
3. **Add cross-tenant check to `_login_client_leadership`** (CRITICAL, security)
4. **Fix `TokenResponse` to include `user_tier`, `is_platform_owner`, `client_id`** (P1 contract)
5. **Add audit emit to `ClientUserService.bootstrap_invite`** (MAJOR, compliance)
6. **Reorder activate flow: commit DB first, then call Supabase** (MAJOR consistency)
7. **Reorder create_user: validate role first, then create Supabase** (MAJOR consistency)
8. **Commit migration 012** (P1 if shipping)
9. **Add response_model to PO bootstrap route** (MINOR, typing)
10. **Align `FakeSupabaseAuth` update semantics with real** (MINOR, test fidelity)
11. **Standardize permission resource names** (MINOR, convention)

## Recommended next step

The two-tier asymmetry (item #1 in the summary) and the missing cross-tenant check (#4) are the most consequential. I'd recommend a grill-me session to finalise the design intent: **should the two tiers share more service code, or is the asymmetry intentional?**

If the answer is "share more," the right refactor is a unified `UserService` with tier-specific strategy classes (CD uses one strategy, app_user uses another). If the answer is "asymmetry is intentional," then the asymmetries need to be documented as D-series decisions in the ADR.

Once that's locked, items 1-7 can be addressed in one focused fix run before re-verifying.
