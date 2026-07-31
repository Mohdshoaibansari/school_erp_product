# Design: Add Config Keys & Module Integration

## Context

C-08 Configuration Framework is built and operational (15 seed keys, 12 endpoints, in-memory cache). Business modules (Fees, Homework) still use hardcoded values. Kernel auth module has 3 hardcoded settings that need to be configurable per tenant.

This change adds 6 new config keys and integrates 3 existing keys into their consuming modules.

## Goals / Non-Goals

**Goals:**
- Add 4 high-priority config keys (auth.jwtExpirySeconds, auth.inviteExpiryDays, auth.passwordResetRedirectUrl, homework.lateSubmissionPolicy)
- Add 2 medium-priority config keys (platform.configDeprecatedHideDays, homework.closedStatusValues)
- Replace hardcoded values in Fees service with `config.get('fee.lateFeePercentage', ...)`
- Replace hardcoded values in Homework service with `config.get('homework.maxAttachmentsPerAssignment', ...)` and `config.get('homework.allowLateSubmission', ...)`
- Establish "config-first" rule in AGENTS.md

**Non-Goals:**
- Migrating existing modules to consume all C-08 keys (only the 3 specified)
- Adding new endpoints or permissions
- Changing the C-08 framework itself
- Building admin UI for config management

## Decisions

### Decision 1: New migration 010 for seed keys

**Choice:** Create `010_add_config_keys.py` migration that inserts 6 new keys into `configuration_key` table.

**Rationale:** Follows the established pattern (migration 009 seeded 15 keys). Keeps seed data versioned and auditable. Each key is inserted with `ON CONFLICT DO NOTHING` for idempotency.

### Decision 2: Module integration via direct import

**Choice:** Import `from kernel.config.resolver import config` directly in service files and call `config.get(key, institution_id=ctx.institution_id)`.

**Rationale:** This is the established pattern from C-08 design. The resolver is a module-level singleton, no DI needed. Works in any context (request, background job, migration).

### Decision 3: homework.lateSubmissionPolicy replaces binary logic

**Choice:** Replace the current `status = "late" if datetime.utcnow().date() > hw.due_date else "submitted"` with a 3-way policy check:
- `"submitted"` — all submissions treated as on-time
- `"late"` — submissions after due date marked as "late"
- `"rejected"` — submissions after due date return 400

**Rationale:** Schools have different policies. Some want grace periods, some want strict deadlines, some want late penalties. A string policy is simpler than a boolean + grace period combo.

### Decision 4: homework.closedStatusValues controls which statuses accept submissions

**Choice:** Replace `if hw.status != "active": raise ValueError(...)` with `if hw.status not in config.get('homework.closedStatusValues', ...): raise ValueError(...)`.

**Rationale:** Some schools want "closed" homework to still accept late submissions (grace period). The config value is a JSON array of status strings that accept submissions.

### Decision 5: Auth module reads config without institution_id for platform-wide keys

**Choice:** `auth.jwtExpirySeconds` and `auth.inviteExpiryDays` are platform-wide keys (no institution_id). `auth.passwordResetRedirectUrl` is also platform-wide.

**Rationale:** JWT expiry and invite expiry are security policies set at the platform level. Individual institutions shouldn't override these (security risk). The config.get() call uses no institution_id, so it always resolves to the platform default.

**Alternative considered:** Per-institution JWT expiry. Rejected — security policies should be consistent across the platform. If a school wants longer sessions, they should use refresh tokens, not longer JWTs.

### Decision 6: AGENTS.md config-first rule

**Choice:** Add to AGENTS.md: "Before building a new business module, first seed its required config keys in C-08. Modules must read from config, not hardcode."

**Rationale:** Establishes the pattern going forward. Every new module (Attendance, Exams, Timetable) will first define its config keys, then build the module that consumes them.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Auth module config.get() adds latency | In-memory cache, O(1) lookup. Negligible impact. |
| homework.lateSubmissionPolicy breaks existing behavior | Default is "submitted" (current behavior is "late"). Need to verify default matches current behavior. |
| Config key typos cause runtime errors | KeyError on config.get() returns 500. Mitigated by: keys are seeded in migration, not user-typed. |
| Per-institution JWT expiry creates security inconsistency | Decision 5: JWT expiry is platform-wide, no institution_id. |

## Migration Plan

1. Create migration `010_add_config_keys.py` with 6 new seed keys
2. Apply migration to cloud Supabase
3. Update `kernel/auth/services/service.py` — replace 3 hardcoded values with config.get()
4. Update `kernel/auth/services/invite_token.py` — replace hardcoded INVITE_JWT_EXPIRY_DAYS
5. Update `kernel/config/resolver.py` — replace hardcoded 90-day threshold
6. Update `business/fees/services/service.py` — replace hardcoded late fee percentage
7. Update `business/homework/services/service.py` — replace hardcoded allowLateSubmission + lateSubmissionPolicy
8. Update AGENTS.md — add config-first rule
9. Run smoke test — verify all changes work with existing seed data
10. Commit

## Open Questions

None. All decisions are locked.
