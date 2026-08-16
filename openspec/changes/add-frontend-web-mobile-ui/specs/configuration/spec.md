# Spec Delta — Configuration (ADDED frontend UI)

> **Change:** add-frontend-web-mobile-ui
> **Domain:** configuration
> **Impact:** ADDED (net-new frontend C-08 UI)
> **Source:** `docs/architecture/adr-frontend-implementation.md` (D6, R5), `docs/prd/frontend-web-mobile.md` (P2-AC-8..P2-AC-10)

---

## ADDED Requirements

### REQ-FE-CFG-01: Browse and Edit Config Keys and Values

The app SHALL provide a Configuration screen where the Institution Admin can browse config keys scoped to the institution and view/edit config values with type-aware input (P2-AC-8).

#### Scenario: Browse keys and edit values
- **WHEN** an Institution Admin opens the Configuration screen
- **THEN** they can browse institution-scoped config keys and view/edit config values with type-aware input

---

### REQ-FE-CFG-02: View Resolved (Effective) Value

The app SHALL allow the Institution Admin to view the resolved (effective) value for a config key, accounting for scope fallbacks (Institution → Client → Platform → default) (P2-AC-9).

#### Scenario: Effective value accounts for fallbacks
- **WHEN** an Institution Admin views a key's resolved value
- **THEN** the app shows the effective value after applying institution/client/platform fallbacks

---

### REQ-FE-CFG-03: View Config Audit Trail

The app SHALL allow the Institution Admin to view the config audit trail (who changed what, when) (P2-AC-10).

#### Scenario: Audit trail visible
- **WHEN** an Institution Admin views the config audit trail
- **THEN** they can see who changed what and when

---

### REQ-FE-CFG-04: All Keys Editable with Backend Validation

The app SHALL treat all config keys as editable; unsafe edits SHALL be blocked by backend validation, not hidden by the UI (R5).

#### Scenario: Unsafe edit rejected by backend
- **WHEN** an Institution Admin edits a key that backend validation considers unsafe
- **THEN** the backend rejects the edit and the app surfaces a friendly error, rather than the UI pre-hiding the key
