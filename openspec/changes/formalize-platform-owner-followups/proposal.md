# Formalize Platform Owner Followups

## Why

During manual E2E testing of the `add-platform-owner-separation` change via the interactive journey-flows UI, several gaps and bugs surfaced that were fixed outside the spec. These corrections are already live in the codebase but not documented anywhere — making it hard for future readers to understand the current behavior. This change formalizes them as proper ADDED requirements so the specs reflect reality.

## What Changes

- New `lookup endpoints` for `institution-types` and `org-unit-types` (needed for institution/org unit creation UI)
- `app_user.institution_id` is **nullable** — Client Directors manage a whole client, not a single institution
- `client_director` role exists with `institution.create` permission (added to DB manually during testing)
- Middleware looks up roles from `app_user` for non-platform-owner users (lookup was removed during refactor, broke normal user login)
- Middleware falls back to looking up `client_id` from `app_user` when no subdomain is provided (Swagger UI compat)
- `homework.grade_submission` uses an explicit `Submission` model import (bug fix — was using `NameError`)
- `SupabaseAuthClient.create_user` uses `httpx` directly, not the Python SDK (SDK sent malformed admin requests)

**No code changes** — this is a documentation-only change. All behaviors are already in production.

## Capabilities

### New Capabilities
- `platform-owner-followups`: One self-contained spec with all 7 formalizations grouped into 3 requirements (Middleware role resolution, Cross-cutting refactors, Client Director lifecycle support).

### Modified Capabilities
- (none — all requirements live in the new spec)

## Impact

- `openspec/specs/` — new `platform-owner-followups/spec.md` file
- No code changes (all behaviors already exist on `main`)
- No breaking changes
