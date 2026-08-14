# configuration-framework — Delta Spec (C-02 User Service Strategy Pattern Refactor)

> **Change:** `refactor-c02-user-service-strategy-pattern`
> **Domain:** C-08 Configuration Framework
> **Delta type:** MODIFIED (RLS plumbing — `app.current_institution_id` added to the session-variable hook)
> **Source:** `docs/architecture/adr-c02-identity-user-management-implementation.md` D10 bug #3; `docs/architecture/audit-c02-implementation-2026-08-03.md`
> **Predecessor:** `openspec/changes/add-c02-user-creation-activation/specs/configuration-framework/spec.md`

This delta is a MODIFIED evolution of the predecessor spec. The predecessor's D5-a addendum (locked 2026-08-03) added a SQLAlchemy `Session "after_begin"` event that sets three RLS session variables: `app.is_platform_owner`, `app.current_client_id`, `app.current_user_id`. This delta adds the fourth: `app.current_institution_id`.

---

## MODIFIED Requirements

### Requirement: RLS hook sets all four session variables from `TenantContext`

The `kernel.db._register_rls_hook` event listener (added by the predecessor's D5-a addendum) sets three RLS session variables on every new transaction: `app.is_platform_owner`, `app.current_client_id`, `app.current_user_id`. This delta requires the hook to ALSO set `app.current_institution_id` from `ctx.institution_id`.

The configuration RLS policies in migration 009 (`current_institution_id()` function, used in 4 places at lines 139, 156, 173, 184) read `app.current_institution_id`. Without this delta, those policies always read NULL and the `OR institution_id = current_institution_id()` branch never matches.

#### Scenario: hook sets `app.current_institution_id` from `ctx.institution_id`
- WHEN the RLS hook fires on a new transaction
- AND the current `TenantContext` has `institution_id=<uuid>`
- THEN the hook SHALL run `SET LOCAL app.current_institution_id = '<uuid>'`
- AND subsequent `current_institution_id()` calls within this transaction SHALL return the UUID

#### Scenario: hook skips `app.current_institution_id` when `ctx.institution_id` is None
- WHEN the RLS hook fires on a new transaction
- AND the current `TenantContext` has `institution_id=None`
- THEN the hook SHALL NOT set `app.current_institution_id` (it remains NULL for the transaction)
- AND `current_institution_id()` SHALL return NULL

#### Scenario: institution-scoped config reads are correct after the fix
- WHEN a user in institution A reads a config value with `scope_type="institution", scope_id=A`
- AND the current `TenantContext` has `institution_id=A`
- THEN the RLS policy's `OR institution_id = current_institution_id()` branch SHALL match
- AND the user SHALL see institution A's config value
- AND the user SHALL NOT see institution B's config values

### Requirement: RLS hook remains contextvar-fresh per transaction

The D5-a addendum required the hook to read `_tenant_context_var` at fire-time so pooled connections reused for subsequent requests fire the hook fresh. This requirement (carried over from the predecessor) is unchanged: the hook reads the contextvar at every `Session "after_begin"` event.

#### Scenario: pool reuses connection for different request
- WHEN connection A is returned to the pool after serving request X
- AND the same connection A is checked out for request Y with a different `TenantContext`
- THEN the RLS hook fires fresh and reads request Y's `TenantContext` (not X's)

## Cross-references

- Predecessor spec: `openspec/changes/add-c02-user-creation-activation/specs/configuration-framework/spec.md` (D5-a addendum)
- ADR: `docs/architecture/adr-c02-identity-user-management-implementation.md` (D5-a, D10 bug #3)
- Audit: `docs/architecture/audit-c02-implementation-2026-08-03.md`
- Migration: `backend/migrations/versions/009_c08_configuration.py` (RLS policies using `current_institution_id()`)
