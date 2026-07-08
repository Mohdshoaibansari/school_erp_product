## Why

C-01 bundles two distinct concerns that should be separated: (1) **kernel infrastructure** that every business module must import (TenantContext, middleware, TenantAwareRepositoryBase, AuditEmitter, TransferCoordinator) — currently trapped inside `kernel/tenant_institution/`, forcing future modules to import from a sibling business package; and (2) **business domain** logic only C-01's own workflows need (Client/Institution/OrgUnit lifecycle, templates, ownership transfer). Extracting infrastructure to `kernel/` and moving domain to `business/tenant_institution/` corrects the dependency direction and establishes the package layout all future modules will follow.

## What Changes

- **EXTRACT** three kernel infrastructure pieces from `kernel/tenant_institution/` to flat `kernel/` files:
  - `TenantAwareRepositoryBase` → `kernel/repo_base.py`
  - `AuditEmitter` + `DefaultAuditEmitter` → `kernel/audit.py`
  - `TransferCoordinator` + `DefaultTransferCoordinator` → `kernel/transfer_coordinator.py`
- **MOVE** all remaining C-01 domain logic from `kernel/tenant_institution/` → `business/tenant_institution/` (models/, repos/, routes/, services/, manifest.py, policies.py, casbin_model.conf, dependencies.py).
- **RENAME** `backend/modules/` → `backend/business/` (placeholder directory).
- **FIX** coupling in `TenantAwareRepositoryBase`: replace `self._model is not Client` with `hasattr(self._model, "client_id")` — drops the business-model import, satisfying kernel→∅ (A3).
- **UPDATE** ~105 import lines across ~38 files: `kernel.tenant_institution.*` → `kernel.*` (infrastructure) or `business.tenant_institution.*` (domain).
- **UPDATE** import-linter contracts to cover extracted kernel files.
- **NO behavioral change** — 167 existing tests must pass unmodified.

## Capabilities

### New Capabilities

_(None — no new behavioral capabilities are introduced.)_

### Modified Capabilities

- `tenant-institution`: No requirements added, modified, or removed. The delta spec is a structural no-op — all 17 requirements / 71 scenarios in `openspec/specs/tenant-institution/spec.md` remain unchanged. The delta exists to record that this refactor touches the capability's implementation (package paths) but not its behavior.

## Impact

- **Code**: ~38 files under `backend/` change import paths; 3 new kernel files created; entire `kernel/tenant_institution/` directory tree moves to `business/tenant_institution/`; `backend/modules/` renamed to `backend/business/`.
- **Tests**: All 167 tests must pass with **zero modifications** (behavior unchanged). Import paths in test files update but test logic does not.
- **Import-linter**: Contracts A3 (kernel→∅) and A4 (acyclic) updated to cover the new kernel files and business→kernel direction.
- **Docs**: Already updated in prior commit (`1d08da2`) — `platform-capabilities-v3.md`, `adr-platform-software-architecture.md`, `c-01-tenant-institution-explained.md`, `docs/business-modules/README.md`.
- **APIs**: No API changes (routes stay the same; only the module path changes).
- **Dependencies**: No new external dependencies. Internal dependency direction corrected (kernel no longer imports from business).