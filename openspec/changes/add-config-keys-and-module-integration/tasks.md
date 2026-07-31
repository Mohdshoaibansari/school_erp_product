# Tasks: Add Config Keys & Module Integration

## 1. Migration: Add 6 new seed keys

- [x] 1.1 Create `backend/migrations/versions/010_add_config_keys.py` with revision chain pointing to `009_c08_configuration`
- [x] 1.2 Add `upgrade()` to insert 6 new keys into `configuration_key`:
  - `auth.jwtExpirySeconds` (number, 3600, Business Rules, auth)
  - `auth.inviteExpiryDays` (number, 7, Business Rules, auth)
  - `auth.passwordResetRedirectUrl` (string, "http://localhost:3000/reset-password", Business Rules, auth)
  - `homework.lateSubmissionPolicy` (string, "submitted", Business Rules, homework)
  - `platform.configDeprecatedHideDays` (number, 90, Platform, config)
  - `homework.closedStatusValues` (json, ["active"], Business Rules, homework)
- [x] 1.3 Add `upgrade()` to insert 6 audit rows (one per key, actor=system)
- [x] 1.4 Add `downgrade()` to delete the 6 keys and 6 audit rows
- [x] 1.5 Apply migration to cloud Supabase and verify: `SELECT COUNT(*) FROM configuration_key` returns 21

## 2. Auth Module Integration (3 high-priority keys)

- [x] 2.1 Update `kernel/auth/services/service.py`: import `from kernel.config.resolver import config`
- [x] 2.2 Replace `timedelta(seconds=3600)` with `timedelta(seconds=config.get('auth.jwtExpirySeconds'))` in JWT minting (platform owner + normal user)
- [x] 2.3 Replace `expires_in: 3600` with `expires_in: jwt_expiry` in all login/refresh response DTOs
- [x] 2.4 Replace `redirect_to = "http://localhost:3000/reset-password"` with `redirect_to = config.get('auth.passwordResetRedirectUrl')`
- [x] 2.5 Update `kernel/auth/services/invite_token.py`: import `from kernel.config.resolver import config`
- [x] 2.6 Replace `INVITE_JWT_EXPIRY_DAYS = 7` with `config.get('auth.inviteExpiryDays')` in token minting
- [x] 2.7 Verify: login returns JWT with correct expiry; invite token uses config expiry; password reset uses config URL

## 3. Config Resolver: Replace hardcoded 90-day threshold

- [x] 3.1 Updated `kernel/config/resolver.py` with `_get_value_internal()` method for self-referencing config lookups
- [x] 3.2 Replaced hardcoded `timedelta(days=90)` with dynamic lookup from `platform.configDeprecatedHideDays`
- [x] 3.3 Updated auto-hide logic to use dynamic threshold
- [x] 3.4 Verified: deprecated key auto-hide works with default 90 days

## 4. Fees Module Integration (1 existing key)

- [x] 4.1 Verified: `fee.lateFeePercentage` is seeded but Fees module does NOT have a late fee calculation yet (only overdue filter). No code change needed — the key is available for when late fee calculation is added in the future.
- [x] 4.2 Verified: Fees module will consume `fee.lateFeePercentage` when late fee calculation is implemented. For now, the key is seeded and ready.

## 5. Homework Module Integration (3 existing keys)

- [x] 5.1 Update `business/homework/services/service.py`: import `from kernel.config.resolver import config`
- [x] 5.2 Replace `if hw.status != "active": raise ValueError(...)` with config-driven `closedStatusValues` check
- [x] 5.3 Replace late submission logic with config-driven `lateSubmissionPolicy` + `allowLateSubmission` check
- [x] 5.4 Verified: `homework.maxAttachmentsPerAssignment` is seeded but Homework module has text-based submissions only (no file attachments). The key is available for when file attachments are added in the future.
- [x] 5.5 Verified: late submission policy works (submitted/late/rejected); allowLateSubmission toggle works

## 6. AGENTS.md: Config-First Rule

- [x] 6.1 Added to AGENTS.md under new section "## 8. Config-First Module Development"
- [x] 6.2 Verified: AGENTS.md is readable and the rule is clear

## 7. Smoke Test

- [x] 7.1 Start backend: backend starts without errors
- [x] 7.2 Login as Platform Owner — 21 keys listed (15 original + 6 new)
- [x] 7.3 Verify `auth.jwtExpirySeconds` resolves to 3600
- [x] 7.4 Verify `homework.lateSubmissionPolicy` resolves to "submitted"
- [x] 7.5 Verify `platform.configDeprecatedHideDays` resolves to 90
- [x] 7.6 Verify `auth.inviteExpiryDays` resolves to 7
- [x] 7.7 Verify `auth.passwordResetRedirectUrl` resolves to http://localhost:3000/reset-password
- [x] 7.8 Verify `homework.closedStatusValues` resolves to ["active"]
- [x] 7.9 Verify login returns `expires_in: 3600` (config-driven)
