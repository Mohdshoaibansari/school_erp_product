# Design — C-02 User Service Strategy Pattern Refactor

> **Change:** `refactor-c02-user-service-strategy-pattern`
> **Source:** `docs/architecture/adr-c02-identity-user-management-implementation.md` (D6-D10); `docs/architecture/audit-c02-implementation-2026-08.md`; spec deltas in `specs/`

## 1. Approach

Replace the two parallel services (`IdentityUserService` for `app_user`, `ClientUserService` for `client_user`) with a single `UserService` that owns a `StrategyResolver` and two strategy classes (`CDStrategy`, `InstitutionUserStrategy`). Keep `AuthService` separate for login, refresh, logout, activate, OTP, password-reset. Both services cooperate on the user-creation → invite → activate flow.

The refactor follows the "Full symmetric strategy interface" decision (D8): both strategies implement every method on the same interface. The service's `StrategyResolver` dispatches based on the operation type (create uses DTO type, other operations use DB lookup). The long-term target is `Organization.type` via `Membership` (D7).

## 2. Architecture diagram

```
┌────────────────────────────────────────────────────────────┐
│                    ROUTES (thin)                          │
│                                                            │
│  POST /api/v1/users                (institution create)    │
│  POST /api/v1/platform/clients/{id}/users  (CD create)   │
│  → DB row + invite JWT only (D11: no Supabase call)      │
│  PATCH /api/v1/users/{id}          (tier-agnostic update)  │
│  GET /api/v1/users/{id}            (tier-agnostic get)     │
│  ...                                                       │
│                                                            │
│  POST /api/auth/login              (AuthService.login)      │
│  POST /api/auth/activate           (AuthService.activate)   │
│  POST /api/auth/otp/request        (AuthService.request_otp)│
│  ...                                                       │
└───────────────────────┬────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼                               ▼
┌────────────────────┐        ┌────────────────────┐
│   UserService      │        │   AuthService      │
│   (NEW — unified)  │        │   (existing,        │
│                    │        │    login/activate)  │
│ - StrategyResolver  │        │ - login (tier       │
│ - audit emit        │        │   dispatch)         │
│ - cross-tenant chk  │        │ - activate          │
│ - create_user       │        │ - request_otp       │
│ - update_user       │        │ - JWT minting       │
│ - delete_user       │        │ - cross-tenant chk  │
│ - get_user          │        │   (on CD branch)    │
│ - list_users        │        │                    │
│ - transition_life…  │        │                    │
└─────────┬──────────┘        └─────────┬──────────┘
          │                              │
          ▼                              ▼
┌──────────────────────────────────────────────────────────┐
│                  StrategyResolver                          │
│                                                            │
│  For create_user(ctx, dto):                               │
│    isinstance(dto, ClientUserCreateDTO) → CDStrategy      │
│    isinstance(dto, UserCreateDTO) → InstitutionUserStrategy│
│                                                            │
│  For other operations:                                    │
│    1. SELECT tier FROM user WHERE id = user_id            │
│    2. Dispatch to corresponding strategy                  │
│                                                            │
│  Long-term: replace with Membership lookup                │
└─────────┬──────────────────────────┬──────────────────────┘
          ▼                          ▼
┌────────────────────┐        ┌────────────────────┐
│    CDStrategy      │        │ InstitutionUserStrategy│
│                    │        │                    │
│ - client_user row  │        │ - app_user row     │
│ - user_tier=       │        │ - user_tier=       │
│   "client_         │        │   "institution"   │
│   leadership"      │        │ - role_assignment  │
│ - ClientUserLifec… │        │ - UserLifecEvent   │
│ - audit emit       │        │ - audit emit       │
│ - cross-tenant chk │        │ - cross-tenant chk │
└────────────────────┘        └────────────────────┘
```

## 3. Strategy interface

```python
class UserStrategy(Protocol):
    """Full-symmetric strategy interface (D8)."""

    async def create_user(self, ctx, dto) -> CreateUserResult: ...
    async def update_user(self, ctx, user_id, dto) -> UserDTO: ...
    async def delete_user(self, ctx, user_id) -> None: ...
    def get_user(self, ctx, user_id) -> UserDTO | None: ...
    def list_users(self, ctx, **filters) -> list[UserDTO]: ...
    async def transition_lifecycle(
        self, ctx, user_id, new_state, reason
    ) -> UserDTO: ...
```

Each strategy implements all six methods. The `StrategyResolver` picks which strategy to call.

## 4. StrategyResolver logic

```python
class StrategyResolver:
    def __init__(self, cd: CDStrategy, inst: InstitutionUserStrategy):
        self._cd = cd
        self._inst = inst

    def resolve_for_create(self, dto) -> UserStrategy:
        """For create_user: dispatch by DTO type."""
        if isinstance(dto, ClientUserCreateDTO):
            return self._cd
        if isinstance(dto, UserCreateDTO):
            return self._inst
        raise TypeError(f"Unknown DTO type: {type(dto)}")

    async def resolve_for_other(self, ctx, user_id) -> UserStrategy:
        """For update/get/delete/list/transition: dispatch by DB lookup."""
        # Read tier from user record
        tier = await self._read_tier(ctx, user_id)
        if tier == "client_leadership":
            return self._cd
        if tier == "institution":
            return self._inst
        raise ValueError(f"Unknown tier for user {user_id}: {tier}")

    async def _read_tier(self, ctx, user_id) -> str:
        """Read tier from user record. Implementation: SELECT tier FROM user WHERE id = user_id."""
        # TODO: implement
        ...
```

## 5. UserService public API

```python
class UserService:
    def __init__(self, session_factory, audit_emitter, resolver: StrategyResolver, ...):
        ...

    async def create_user(self, ctx, dto) -> dict:
        strategy = self._resolver.resolve_for_create(dto)
        return await strategy.create_user(ctx, dto)

    async def update_user(self, ctx, user_id, dto) -> UserDTO:
        strategy = await self._resolver.resolve_for_other(ctx, user_id)
        return await strategy.update_user(ctx, user_id, dto)

    def get_user(self, ctx, user_id) -> UserDTO | None:
        # ...
    
    # ... etc.
```

## 6. AuthService changes (login dispatch + fixes)

The `AuthService.login` method already dispatches by `user_metadata.user_tier`. This refactor adds the cross-tenant check to the CD branch (D10 bug #4):

```python
async def login(self, ctx, email, password, *, ip_address=None, user_agent=None):
    result = await self._supabase.sign_in_with_password(email, password)
    supabase_user = result.get("user", {})
    user_id = uuid.UUID(supabase_user["id"])
    user_metadata = supabase_user.get("user_metadata") or {}

    if user_metadata.get("is_platform_owner"):
        return await self._login_platform_owner(...)

    user_tier = user_metadata.get("user_tier")
    if user_tier == "client_leadership":
        # NEW: cross-tenant check
        if ctx.client_id and user_obj.client_id != ctx.client_id and "platform_owner" not in (ctx.roles or []):
            raise AuthError("Access denied. Account does not belong to this client.", 403)
        return await self._login_client_leadership(...)

    if user_tier != "institution":
        raise AuthError("Account requires reconfiguration. Contact administrator.", 403)
    # institution user path with cross-tenant check (already present)
    ...
```

## 7. Activate flow (D10 bug #5 + D11)

The activate flow creates the Supabase Auth user WITH password after DB commit:

```python
async def activate(self, ctx, invite_token, password):
    token_data = verify_invite_token(invite_token)
    user_id = token_data["user_id"]

    # Phase 1: Elevated session — resolve identity
    with self._session_factory() as session:
        set_rls_session_vars(session, is_platform_owner=True)
        client_user_obj = session.get(ClientUser, user_id)
        if client_user_obj:
            tier = "client_leadership"
            user_client_id = client_user_obj.client_id
            user_institution_id = None
        else:
            user_obj = session.get(User, user_id)
            if not user_obj:
                raise AuthError("User not found", 404)
            tier = "institution"
            user_client_id = user_obj.client_id
            user_institution_id = user_obj.institution_id

    # Phase 2: DB work with proper RLS vars
    with self._session_factory() as session:
        set_rls_session_vars(session, user_id=user_id, client_id=user_client_id, institution_id=user_institution_id)
        # ... set lifecycle_status = "active" + lifecycle event ...
        session.commit()

    # Phase 3: Create Supabase Auth user WITH password (D11)
    await self._supabase.create_user(
        user_id, email,
        password=password,
        user_metadata={"user_tier": tier},
    )

    # Phase 4: Audit (actor = user_id from token)
    self._audit.emit(...)

    return {"message": "User activated successfully", "user_id": str(user_id), "user_tier": tier, "client_slug": slug}
```

Key design points:

- **D11:** Supabase user is created WITH password in a single `POST /admin/users` call. No `update_user` call.
- **A6 invariant preserved:** `_tenant_context_var` is NOT mutated by the service.
- **Trust boundary is the invite token:** the token is cryptographically signed. Once verified, the `user_id` is trusted.
- **Two-session pattern:** one for elevated lookup, one for the actual work with proper RLS vars.
- **Saga retry for Supabase failure:** if Supabase fails after DB commit, the user record is in `active` state but has no Supabase Auth user. A background retry job (out of scope) would re-attempt.

## 8. RLS hook update (D10 bug #3)

The hook adds `app.current_institution_id`:

```python
@event.listens_for(Session, "after_begin")
def _set_rls_vars(session, transaction, connection):
    ctx = _tenant_context_var.get()
    if ctx is None:
        return

    is_po = "true" if ctx.is_platform_owner else "false"
    connection.execute(text(f"SET LOCAL app.is_platform_owner = '{is_po}'"))

    if ctx.client_id is not None:
        connection.execute(text(f"SET LOCAL app.current_client_id = '{ctx.client_id}'"))

    if ctx.institution_id is not None:                                          # NEW
        connection.execute(text(f"SET LOCAL app.current_institution_id = '{ctx.institution_id}'"))

    if ctx.user_id is not None:
        connection.execute(text(f"SET LOCAL app.current_user_id = '{ctx.user_id}'"))
```

## 8.5. `set_rls_session_vars` helper for unauthenticated flows (D6 grill-me session)

The activate flow operates on an unauthenticated request — the user is NOT logged in, so `ctx.user_id` is `None` and the RLS hook sets `app.current_user_id` to `None`. The RLS policies on `client_user` (`client_user_cd_select_own`) and `app_user` (`current_user_id`) require a non-NULL `id = current_setting('app.current_user_id')::uuid` — so the user lookup FAILS.

To handle this, a new public function is added to `kernel/db.py`:

```python
def set_rls_session_vars(
    session,
    *,
    user_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
    institution_id: uuid.UUID | None = None,
    is_platform_owner: bool = False,
) -> None:
    """Set RLS session variables explicitly on a session.

    Use this for bootstrap flows where the middleware's TenantContext is
    incomplete (e.g., activate where the user is not yet authenticated).

    The service is responsible for verifying the values before calling this
    function. For activate, the user_id comes from a cryptographically signed
    invite token. The client_id and institution_id come from a DB lookup.

    Each SET LOCAL applies to the current transaction only.
    """
    if is_platform_owner:
        session.execute(text("SET LOCAL app.is_platform_owner = 'true'"))
    if user_id is not None:
        session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    if client_id is not None:
        session.execute(text(f"SET LOCAL app.current_client_id = '{client_id}'"))
    if institution_id is not None:
        session.execute(text(f"SET LOCAL app.current_institution_id = '{institution_id}'"))
```

The activate service uses it in a two-session pattern:

```python
async def activate(self, ctx, invite_token, password):
    # Phase 1: Resolve identity from the verified invite token
    token_data = verify_invite_token(invite_token)
    user_id = token_data["user_id"]

    async with self._session_factory() as session:
        # Privileged session — trust the invite token
        set_rls_session_vars(session, is_platform_owner=True)
        # Look up the user's full identity
        client_user_obj = session.get(ClientUser, user_id)
        if client_user_obj:
            tier = "client_leadership"
            user_client_id = client_user_obj.client_id
            user_institution_id = None
        else:
            user_obj = session.get(User, user_id)
            if not user_obj:
                raise AuthError("User not found", 404)
            tier = "institution"
            user_client_id = user_obj.client_id
            user_institution_id = user_obj.institution_id

    # Phase 2: Do the activate work with the proper identity
    async with self._session_factory() as session:
        set_rls_session_vars(
            session,
            user_id=user_id,
            client_id=user_client_id,
            institution_id=user_institution_id,
        )
        # Look up the user again (RLS now works because we set the vars)
        # ... set lifecycle_status = "active" + lifecycle event ...
        # ... commit ...

    # Phase 3: Supabase (no DB)
    await self._supabase.update_user(user_id, password=password, email_confirm=True)

    # Phase 4: Audit (actor = user_id from token, not ctx.user_id which is None)
    self._audit.emit(
        action="user_activated",
        client_id=user_client_id,
        institution_id=user_institution_id,
        actor=user_id,  # from the invite token
        payload={...},
    )

    return ActivateResponse(
        message="User activated successfully",
        user_id=str(user_id),
        user_tier=tier,
        client_slug=<from lookup>,
    )
```

Key design points:

- **A6 invariant preserved:** `_tenant_context_var` is NOT mutated by the service. The full identity is held in memory, not in the contextvar.
- **Trust boundary is the invite token:** the token is cryptographically signed. Once verified, the `user_id` is trusted. The `client_id` and `institution_id` come from the database (read in the same lookup session).
- **No new RLS policies required:** the existing RLS policies work once the session vars are set correctly.
- **No middleware change:** the middleware's initial ctx (subdomain-only) is the same as before. The activate service handles the bootstrap internally.
- **Two-session pattern:** one short-lived session for the privileged lookup, one session for the actual work with proper RLS vars. Both are short-lived. The cost is one extra session round-trip on a one-time activation flow.
- **Saga retry for Supabase failure:** the predecessor's D10 bug #5 ordering (commit DB first, then call Supabase) is preserved. If Supabase fails after DB commit, the user record is in `active` state but has no password in Supabase. A background retry job (out of scope) would re-attempt the Supabase call.

## 9. FakeSupabaseAuth overwrite (D10 bug #9)

```python
async def update_user(self, user_id, *, password=None, email=None, email_confirm=None, user_metadata=None):
    # ...
    if user_metadata is not None:
        user["user_metadata"] = user_metadata  # CHANGED: was .update(user_metadata)
    # ...
```

## 10. Migration path

The refactor is a code-only change **plus one schema migration** for D12 (`user_account` parent table). The 4 spec files become modified relative to the predecessor change. The predecessor change (`add-c02-user-creation-activation`) is archived separately.

### D12 Schema Migration (015)

```sql
-- Step 1: Create user_account table
CREATE TABLE user_account (
    id UUID PRIMARY KEY
);

-- Step 2: Backfill from existing app_user + client_user rows
INSERT INTO user_account (id) SELECT id FROM app_user;
INSERT INTO user_account (id) SELECT id FROM client_user
    ON CONFLICT (id) DO NOTHING;  -- in case of UUID overlap

-- Step 3: Add FK on app_user.id → user_account.id
ALTER TABLE app_user ADD CONSTRAINT app_user_id_fkey
    FOREIGN KEY (id) REFERENCES user_account(id);

-- Step 4: Add FK on client_user.id → user_account.id
ALTER TABLE client_user ADD CONSTRAINT client_user_id_fkey
    FOREIGN KEY (id) REFERENCES user_account(id);

-- Step 5-6: role_assignment FK change
ALTER TABLE role_assignment DROP CONSTRAINT role_assignment_user_id_fkey;
ALTER TABLE role_assignment ADD CONSTRAINT role_assignment_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES user_account(id);

-- Step 7-8: login_attempt FK change
ALTER TABLE login_attempt DROP CONSTRAINT login_attempt_user_id_fkey;
ALTER TABLE login_attempt ADD CONSTRAINT login_attempt_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES user_account(id);
```

### Code Changes (existing tasks + D12 additions)

Steps:
1. Create `StrategyResolver` class
2. Create `CDStrategy` class (D11: no Supabase call; D12: inserts `user_account` first, then `role_assignment`)
3. Create `InstitutionUserStrategy` class (D11: no Supabase call; D12: inserts `user_account` first)
4. Create new `UserService` that holds the resolver
5. Update `kernel/user/dependencies.py` to return new `UserService`
6. Update `kernel/business/tenant_institution/dependencies.py` for the bootstrap route
7. Delete `kernel/user/services/client_user_service.py`
8. Update `kernel/auth/services/service.py` — D11: activate creates Supabase user with password; D12: `login_attempt` insert works for CDs
9. Update `kernel/auth/routes/auth.py` to add `LoginResponse` model, use it in login route
10. Update `kernel/auth/supabase_client.py` — D11: add `password` parameter to `create_user`
11. Update `kernel/db.py` to add `app.current_institution_id` to the RLS hook
12. Update `backend/tests/fake_supabase_auth.py` — D11: add `password` parameter to `create_user`; D10 bug #9: overwrite semantics
13. Update `backend/tests/test_c02_user.py` and `backend/tests/test_c03_auth.py` to match new behavior
14. Commit `backend/migrations/versions/012_app_user_institution_id_not_null.py` to git
15. **D12:** Create `UserAccount` model in `kernel/user/models/`
16. **D12:** Update `AppUser` and `ClientUser` models with FK to `UserAccount`
17. **D12:** Update `user_repo.create()` to insert `user_account` first
18. **D12:** Update `client_user_repo.create()` to insert `user_account` first
19. **D12:** Update `RoleAssignment` and `LoginAttempt` models with FK to `UserAccount`
20. **D12:** Create migration `015_user_account_parent_table.py`
21. **D12:** Update CDStrategy to insert `role_assignment` (now works)
22. **D12:** Update `bootstrap.py` to insert `user_account` first

## 11. Tradeoffs

| Decision | Pro | Con |
|---|---|---|
| Unified `UserService` | One mental model; symmetric interface forces both strategies to implement same methods | Larger class; dispatch logic in one place |
| DTO type for create dispatch | Type system enforces tier; no new field | Requires `isinstance` check, which some find un-Pythonic |
| DB lookup for other operations | Single source of truth (the user record) | Adds a SELECT round-trip per operation |
| Full symmetric strategy interface | Forces parity; catches asymmetries at instantiation | Slight duplication of "delete user" logic between strategies |
| `LoginResponse` with optional fields | Frontend gets all tier data without separate `/me` call | Some fields are always None for some tiers — slight noise in response |
| Commit DB first in activate | Reduces Supabase-state-ahead-of-DB risk | If Supabase fails, DB is ahead — saga retry needed |

## 12. Open issues

- **Saga retry mechanism** for activate flow: if DB commits but Supabase fails, who retries? Options: a background job, an explicit user-initiated retry, or a manual recovery script. This is out of scope for this refactor but flagged for C-09 follow-up.
- **`Membership` model** is the long-term dispatch target (D7). The Membership schema is a future capability.
- **Permission resource name**: standardize on `user` or `client_user`? Per D10 bug #10, we standardize on `user` and let the strategy determine tier at runtime. The Casbin policies use `user:create`, `user:read`, etc. The CD-specific permissions (`client:create`, `institution:create`) stay as they are.
