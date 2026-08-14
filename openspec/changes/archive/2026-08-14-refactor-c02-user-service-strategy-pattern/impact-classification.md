# Impact Classification — C-02 User Service Strategy Pattern Refactor

> **Status:** Impact classification (input to prd-to-sdd phase)
> **Capability:** C-02 Identity & User Management (intersecting C-03 Authentication, Kernel/Auth infrastructure)
> **Decisional inputs:** `docs/architecture/adr-c02-identity-user-management-implementation.md` (D6-D10 added 2026-08-03), `docs/architecture/audit-c02-implementation-2026-08-03.md` (integration audit)
> **Predecessor:** `openspec/changes/add-c02-user-creation-activation/` (currently in flight, PARTIAL verify)
> **Verification:** `openspec list --specs` returns existing specs at `add-c02-user-creation-activation/specs/{identity-user-management,authentication,configuration-framework,auth-infrastructure}/spec.md`. No `openspec/specs/` (archive) content.

---

## Classification
- Domain status: **EXISTING** (4 domains with delta specs from the predecessor change)
- Delta type: **MODIFIED** (all 4 domains change behavior — service architecture refactor)
- Cross-cutting: **YES** — affects 4 domains
- Recommended OpenSpec domain names: same 4 from predecessor: `identity-user-management`, `authentication`, `configuration-framework`, `auth-infrastructure`
- Recommended OpenSpec change name: `refactor-c02-user-service-strategy-pattern`

## Reasoning

This is a follow-up refactor change to `add-c02-user-creation-activation`. The predecessor change created the specs for these 4 domains; this refactor MODIFIES the behavior in all 4 of them:

- **`identity-user-management`** — `IdentityUserService` is replaced by a new `UserService` with `StrategyResolver` and two strategies. The behavior is the same end-to-end, but the internal architecture changes. This is a MODIFIED delta because the same domain already has a spec in the predecessor change.
- **`authentication`** — `AuthService` keeps the same public methods but the login flow now dispatches to a tier-specific strategy internally, the activate flow is reordered to commit DB first, `_login_client_leadership` adds a cross-tenant check, and `request_otp` signature is fixed. This is MODIFIED.
- **`configuration-framework`** — `app.current_institution_id` is added to the RLS hook in `kernel/db.py`, which fixes a config-read RLS misbehavior. The configuration_key table is unchanged; the behavior change is in the session-variable plumbing. This is MODIFIED.
- **`auth-infrastructure`** — the `SupabaseAuthClientImpl.update_user` signature was already fixed (bug #1). New: `FakeSupabaseAuth.update_user` uses overwrite semantics (bug #9). This is MODIFIED.

All four domains have prior specs in the predecessor change. None has an OpenSpec archive (`openspec/specs/` is empty), so the "MODIFIED" delta is relative to the predecessor's own delta, not to a baseline.

## ADDED / MODIFIED / REMOVED summary

| Domain | Tag | What changes |
|---|---|---|
| identity-user-management | MODIFIED | `IdentityUserService` replaced by `UserService` + strategies. `ClientUserService` deleted. DTO class type becomes the tier discriminator. Same end-to-end behavior, but internal architecture is reorganized. |
| authentication | MODIFIED | `AuthService.login` dispatches to a tier strategy internally (PO/CD/institution). `_login_client_leadership` adds cross-tenant check. Activate flow reorders: commit DB first, then call Supabase. `request_otp` signature fixed. `LoginResponse` is the new unified model with optional tier fields. |
| configuration-framework | MODIFIED | `app.current_institution_id` is added to the RLS hook in `kernel/db.py`. This fixes institution-scoped config reads. The configuration_key table is unchanged. |
| auth-infrastructure | MODIFIED | `FakeSupabaseAuth.update_user` uses overwrite semantics (not merge). Other fixes (user_metadata param, RLS hook) were applied in the predecessor change. |

## ADDED requirements (high-level, to become spec scenarios)

### identity-user-management

- **`UserService` exists as the single user-lifecycle service.** It replaces `IdentityUserService` and `ClientUserService`. The class has a `StrategyResolver` that dispatches to `CDStrategy` or `InstitutionUserStrategy` based on the operation and DTO type.
- **`StrategyResolver` for create dispatches on DTO type.** `isinstance(dto, ClientUserCreateDTO)` → `CDStrategy`. `isinstance(dto, UserCreateDTO)` → `InstitutionUserStrategy`.
- **`StrategyResolver` for other operations dispatches by DB lookup.** `get_user`, `update_user`, `delete_user`, `list_users`, `transition_lifecycle` first read the user record (by ID or filter) to determine the tier, then call the corresponding strategy.
- **Both strategies emit audit events symmetrically.** `CDStrategy.create_user` emits `action="user_created"` with payload `{user_id, email, name, client_id}`. `InstitutionUserStrategy.create_user` emits the same with `{user_id, email, name, institution_id}`.
- **Both strategies do cross-tenant checks.** `CDStrategy.login` checks `ctx.client_id == user_obj.client_id`. `InstitutionUserStrategy.login` does the same (already present in the predecessor).
- **Both strategies return the unified response shape.** `create_user` returns `{user, invite_url}`. `login` returns `LoginResponse` with `user_tier` and `client_id` populated for the relevant tier.
- **Long-term evolution:** `StrategyResolver` will switch to `Organization.type` via `Membership` once that abstraction exists. The current DTO-type dispatch is a stepping stone.

### authentication

- **`AuthService` keeps login/refresh/logout/activate/OTP/password-reset methods.** It is the separate authentication service (D6).
- **`AuthService.login` dispatches to a tier-specific JWT minting flow.** PO → custom HS256 with `is_platform_owner: True`. CD → custom HS256 with `{sub, user_tier, client_id, role_id}`. Institution → Supabase access token from `sign_in_with_password`.
- **`LoginResponse` is unified.** Fields: `access_token, refresh_token, token_type, expires_in, is_platform_owner: bool | None, user_tier: str | None, client_id: uuid.UUID | None`.
- **Activate flow reorders to commit DB first.** The `session.commit()` happens BEFORE `await self._supabase.update_user(...)`. If Supabase fails, the DB rollback is impossible — the system uses a saga or eventual-consistency retry.
- **`request_otp` signature includes `ip_address: str | None = None`.** Route extracts `client_ip` and passes it.
- **`_login_client_leadership` (or its replacement) does a cross-tenant check.** `if ctx.client_id and user_obj.client_id != ctx.client_id and "platform_owner" not in (ctx.roles or []): raise AuthError(403)`.

### configuration-framework

- **RLS hook in `kernel/db.py` sets `app.current_institution_id`.** The hook now sets all four RLS session variables from the `TenantContext`: `app.is_platform_owner`, `app.current_client_id`, `app.current_institution_id`, `app.current_user_id`.
- **Institution-scoped config reads are correct.** The `current_institution_id()` function in migration 009 returns the user's institution, so RLS policies that check `OR institution_id = current_institution_id()` now work.

### auth-infrastructure

- **`FakeSupabaseAuth.update_user` uses overwrite semantics.** The `user_metadata` parameter is assigned (`user["user_metadata"] = user_metadata`), not merged. This matches the real `SupabaseAuthClientImpl.update_user` behavior.
- **`FakeSupabaseAuth.update_user` signature has `user_metadata: dict | None = None`.** Already present from the predecessor; this refactor verifies it's the overwrite variant.
- **RLS session variables continue to be set on endpoint sessions.** Already done in the predecessor (D5-a fix). The refactor verifies `app.current_institution_id` is included.

## MODIFIED behavior (carry-over from the 10 audit bugs in D10)

The 10 audit bugs from the 2026-08-03 audit are folded into this refactor per D10. Their `MODIFIED` status against the predecessor's specs:

| # | Bug | Where in predecessor spec | Where in this refactor spec |
|---|-----|---------------------------|-------------------------------|
| 1 | `update_user` NameError | Already fixed in predecessor (T-01) | Carry-over; verify |
| 2 | `TokenResponse` strips tier fields | (predecessor spec says response is `{access_token, refresh_token, token_type, expires_in}` — not wrong, but incomplete) | This refactor: response is `LoginResponse` with optional tier fields |
| 3 | `app.current_institution_id` not set in RLS hook | (predecessor spec says three RLS vars are set) | This refactor: four RLS vars are set |
| 4 | Missing cross-tenant check on CD login | (predecessor spec doesn't mention) | This refactor: cross-tenant check on CD login (NEW requirement) |
| 5 | Activate flow commits AFTER Supabase call | (predecessor spec says commit happens — order unspecified) | This refactor: commit BEFORE Supabase call (NEW ordering requirement) |
| 6 | `create_user` validates role AFTER Supabase create | (predecessor spec says role validated — order unspecified) | This refactor: validate role BEFORE Supabase create (NEW ordering requirement) |
| 7 | Migration 012 untracked in git | n/a (infrastructure, not in spec) | This refactor: `git add` the file |
| 8 | `ClientUserService.bootstrap_invite` doesn't emit audit | (predecessor spec says audit emitted) | This refactor: strategy emits audit symmetrically |
| 9 | `FakeSupabaseAuth.update_user` merge vs overwrite | (predecessor spec doesn't specify) | This refactor: overwrite semantics |
| 10 | Permission resource name `user` vs `client_user` | n/a (Casbin config, not in spec) | This refactor: standardize on `user` (the strategy determines tier at runtime, not the permission name) |

## Boundary relationships (NOT modifications)

| Relationship | Direction | Other capability | Why not a modification |
|---|---|---|---|
| `UserService` uses `UserRepository` and `ClientUserRepository` | C-02 → C-02 | (same capability) | The repositories already exist; the service just stops being two classes. No schema change. |
| `UserService` calls `mint_invite_token` from `kernel.auth.services.invite_token` | C-02 → C-03 | C-03 Authentication | C-03 owns `mint_invite_token`; C-02 consumes it. Read-consume relationship, not a modification. |
| `UserService` calls `config.get("app.activationBaseUrl")` | C-02 → C-08 | C-08 Config | C-08 owns config keys; C-02 accesses via `config.get()`. Consumer relationship. |
| Strategy pattern uses `TenantContext` | C-02 → Kernel | Kernel | Kernel owns `TenantContext`; C-02 consumes it. |
| Login flow uses Casbin (for tier permission check) | C-02 → C-04 | C-04 Authorization | C-04 owns the Casbin enforcer; C-02's permission is `user:create` and `user:read`. No new permissions are added in this refactor. |

## Artifacts to produce

| Artifact | Path | Note |
|---|---|---|
| proposal.md | `openspec/changes/refactor-c02-user-service-strategy-pattern/proposal.md` | This file (done) |
| impact-classification.md | `openspec/changes/refactor-c02-user-service-strategy-pattern/impact-classification.md` | This file (done) |
| specs/identity-user-management/spec.md | `openspec/changes/refactor-c02-user-service-strategy-pattern/specs/identity-user-management/spec.md` | To create — MODIFIED delta (strategy pattern, audit symmetry, cross-tenant) |
| specs/authentication/spec.md | `openspec/changes/refactor-c02-user-service-strategy-pattern/specs/authentication/spec.md` | To create — MODIFIED delta (LoginResponse, login dispatch, activate ordering, request_otp fix, cross-tenant) |
| specs/configuration-framework/spec.md | `openspec/changes/refactor-c02-user-service-strategy-pattern/specs/configuration-framework/spec.md` | To create — MODIFIED delta (app.current_institution_id) |
| specs/auth-infrastructure/spec.md | `openspec/changes/refactor-c02-user-service-strategy-pattern/specs/auth-infrastructure/spec.md` | To create — MODIFIED delta (Fake overwrite) |
| design.md | `openspec/changes/refactor-c02-user-service-strategy-pattern/design.md` | To create — architecture diagram, strategy interface, resolver logic, migration path |
| tasks.md | `openspec/changes/refactor-c02-user-service-strategy-pattern/tasks.md` | To create — checkable implementation tasks |
| verify.md | `openspec/changes/refactor-c02-user-service-strategy-pattern/verify.md` | To create after apply |
| docs/prd/c-02-refactor.md | `docs/prd/c-02-refactor.md` | To create — product-first PRD for the refactor (matches existing C-02 pattern) |

## Boundary relationships (NOT modifications)

The 4 affected domains' specs already exist in the predecessor change. This refactor's specs are MODIFIED deltas that supersede portions of the predecessor. The 4 spec files in this refactor will reference the predecessor specs and explicitly state which requirements are unchanged, added, or removed.

The predecessor change (`add-c02-user-creation-activation`) remains in flight. It will be archived separately after its verify is complete (the bug fixes in D10 are NOT required for the predecessor's archive; the predecessor is the original D1-D5 change without the refactor).
