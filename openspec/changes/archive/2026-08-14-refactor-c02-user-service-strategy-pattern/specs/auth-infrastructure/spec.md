# auth-infrastructure — Delta Spec (C-02 User Service Strategy Pattern Refactor)

> **Change:** `refactor-c02-user-service-strategy-pattern`
> **Domain:** Kernel / Auth Infrastructure (spanning `supabase_client.py`, `fake_supabase_auth.py`, middleware/session plumbing)
> **Delta type:** MODIFIED (test-fidelity fix: `FakeSupabaseAuth.update_user` uses overwrite semantics; D11: `create_user` gains `password` parameter)
> **Source:** `docs/architecture/adr-c02-identity-user-management-implementation.md` D10 bug #9, D11
> **Predecessor:** `openspec/changes/add-c02-user-creation-activation/specs/auth-infrastructure/spec.md`

This delta is a MODIFIED evolution of the predecessor spec. The predecessor's D5 fix added `user_metadata` parameter handling to both the real `SupabaseAuthClientImpl.update_user` and `FakeSupabaseAuth.update_user`. This delta fixes a test-fidelity gap (D10 bug #9), adds the `password` parameter to `create_user` (D11), and introduces the `user_account` parent table (D12).

---

## MODIFIED Requirements

### Requirement: `user_account` parent table exists (D12)

A `user_account` table SHALL exist with a single column `id UUID PRIMARY KEY`. Both `app_user.id` and `client_user.id` SHALL have FK constraints to `user_account.id`. The `role_assignment.user_id` and `login_attempt.user_id` FKs SHALL point to `user_account.id` instead of `app_user.id`.

#### Scenario: user_account table created
- WHEN the migration is applied
- THEN a `user_account` table SHALL exist with `id UUID PRIMARY KEY`
- AND `app_user.id` SHALL have a FK to `user_account.id`
- AND `client_user.id` SHALL have a FK to `user_account.id`

#### Scenario: existing rows backfilled
- WHEN the migration runs on a database with existing `app_user` and `client_user` rows
- THEN the migration SHALL insert a `user_account` row for every existing `app_user.id` and `client_user.id`
- AND the FK creation on the child tables SHALL succeed (no orphaned rows)

#### Scenario: role_assignment FK updated
- WHEN the migration is applied
- THEN the FK `role_assignment_user_id_fkey` SHALL point to `user_account.id` (not `app_user.id`)
- AND inserting a `role_assignment` with `user_id` pointing to a `client_user` UUID SHALL succeed

#### Scenario: login_attempt FK updated
- WHEN the migration is applied
- THEN the FK `login_attempt_user_id_fkey` SHALL point to `user_account.id` (not `app_user.id`)
- AND inserting a `login_attempt` with `user_id` pointing to a `client_user` UUID SHALL succeed

### Requirement: `SupabaseAuthClient.create_user` accepts optional `password` parameter (D11)

The `create_user` method on both the Protocol and the implementation SHALL accept an optional `password: str | None = None` keyword-only parameter. When provided, the `POST /auth/v1/admin/users` payload SHALL include `"password": password`. When omitted, the user is created with no password (as before).

The FakeSupabaseAuth SHALL also accept and store the password.

#### Scenario: create_user with password
- WHEN `await supabase.create_user(user_id, email, password="secure123", user_metadata={...})` is called
- THEN the `POST /auth/v1/admin/users` payload SHALL include `"password": "secure123"`
- AND the user SHALL be created with that password
- AND the user SHALL be able to sign in with `sign_in_with_password(email, "secure123")`

#### Scenario: create_user without password (backward compatible)
- WHEN `await supabase.create_user(user_id, email, user_metadata={...})` is called (no password)
- THEN the `POST /auth/v1/admin/users` payload SHALL NOT include `"password"`
- AND the user SHALL be created with no password
- AND existing callers SHALL NOT break

### Requirement: `FakeSupabaseAuth.update_user` uses overwrite semantics for `user_metadata`

`SupabaseAuthClientImpl.update_user` (the real implementation in `backend/kernel/auth/supabase_client.py:271-272`) uses:
```python
if user_metadata is not None:
    update_data["user_metadata"] = user_metadata
```

This is **overwrite** semantics: passing `user_metadata={"other_key": "x"}` REPLACES the entire `user_metadata` dict.

`FakeSupabaseAuth.update_user` (the test fake in `backend/tests/fake_supabase_auth.py:168-169`, modified by the predecessor's D5 fix) uses:
```python
if user_metadata is not None:
    user["user_metadata"].update(user_metadata)
```

This is **merge** semantics: passing `user_metadata={"other_key": "x"}` PRESERVES existing keys and only adds/overrides the passed ones.

This divergence is a test-fidelity bug. If a real implementation call passes `user_metadata={"user_tier": "institution"}` to overwrite a previously-set `user_tier="client_leadership"`, the real impl correctly overwrites, but the fake would preserve the old value. Tests using the fake would not catch a regression where the real impl accidentally falls back to merge semantics.

This delta requires the fake to use overwrite semantics to match the real impl.

#### Scenario: first call sets `user_tier="institution"`
- WHEN `fake.update_user(user_id, user_metadata={"user_tier": "institution"})` is called
- AND the user record has no `user_metadata` set yet
- THEN the fake SHALL set `user["user_metadata"] = {"user_tier": "institution"}` (overwrite from empty)

#### Scenario: second call overwrites `user_metadata`
- WHEN the user record has `user_metadata = {"user_tier": "client_leadership", "other": "x"}`
- AND `fake.update_user(user_id, user_metadata={"user_tier": "institution"})` is called
- THEN the fake SHALL REPLACE the entire dict: `user["user_metadata"] = {"user_tier": "institution"}`
- AND `user["user_metadata"]` SHALL NOT contain `"other": "x"` anymore

#### Scenario: parity with real impl
- WHEN the fake is used in a test that calls `update_user` twice with different `user_metadata` dicts
- AND the real impl is exercised in production with the same pattern
- THEN the test SHALL pass with the same outcome as production
- AND the fake SHALL NOT preserve keys that the real impl would replace

## Cross-references

- Predecessor spec: `openspec/changes/add-c02-user-creation-activation/specs/auth-infrastructure/spec.md`
- ADR: `docs/architecture/adr-c02-identity-user-management-implementation.md` (D10 bug #9)
- Audit: `docs/architecture/audit-c02-implementation-2026-08-03.md`
- Real impl: `backend/kernel/auth/supabase_client.py:271-272`
- Fake: `backend/tests/fake_supabase_auth.py:168-169`
