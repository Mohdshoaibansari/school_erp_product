# Proposal: Add Config Keys & Module Integration

## Why

The C-08 Configuration Framework is built and seeded with 15 keys, but business modules (Fees, Homework) still use hardcoded values. Additionally, several high-priority settings (JWT expiry, password reset URL, invite expiry) are hardcoded in the kernel auth module and need to be configurable per tenant.

This change:
1. Adds 6 new config keys (4 high priority, 2 medium priority)
2. Integrates 3 existing seeded keys into Fees and Homework modules
3. Establishes a "config-first" rule for future module development

## What Changes

### New Config Keys (6 keys)

| Key | Type | Default | Category | Module | Priority |
|-----|------|---------|----------|--------|----------|
| `auth.jwtExpirySeconds` | number | 3600 | Business Rules | auth | High |
| `auth.inviteExpiryDays` | number | 7 | Business Rules | auth | High |
| `auth.passwordResetRedirectUrl` | string | `http://localhost:3000/reset-password` | Business Rules | auth | High |
| `homework.lateSubmissionPolicy` | string | `"submitted"` | Business Rules | homework | High |
| `platform.configDeprecatedHideDays` | number | 90 | Platform | config | Medium |
| `homework.closedStatusValues` | json | `["active"]` | Business Rules | homework | Medium |

### Module Integration (3 existing keys)

| Existing Key | Module | Current Hardcoded | Change |
|-------------|--------|-------------------|--------|
| `fee.lateFeePercentage` | Fees | `2` in service.py | Replace with `config.get('fee.lateFeePercentage', institution_id=...)` |
| `homework.maxAttachmentsPerAssignment` | Homework | `5` in dtos.py | Replace with `config.get('homework.maxAttachmentsPerAssignment', institution_id=...)` |
| `homework.allowLateSubmission` | Homework | `false` in service.py | Replace with `config.get('homework.allowLateSubmission', institution_id=...)` |

### Config-First Rule (AGENTS.md)

Add to AGENTS.md: "Before building a new business module, first seed its required config keys in C-08. Modules must read from config, not hardcode."

## Capabilities

### New Capabilities
- None (all changes are within existing capabilities)

### Modified Capabilities
- `configuration` — 6 new keys added to seed catalog
- Fees module — 1 hardcoded value replaced with config lookup
- Homework module — 2 hardcoded values replaced with config lookups

## Impact

- **C-08**: 6 new seed keys (new migration 010)
- **Fees**: `service.py` — 1 line changed (late fee calculation)
- **Homework**: `service.py` — 2 lines changed (max attachments, late submission policy)
- **Auth**: `service.py` — 3 hardcoded values replaced with config lookups (JWT expiry, invite expiry, redirect URL)
- **Config resolver**: 90-day threshold now reads from config instead of hardcoded
- **AGENTS.md**: New config-first rule added
- **No new tables, no new endpoints, no new permissions**
