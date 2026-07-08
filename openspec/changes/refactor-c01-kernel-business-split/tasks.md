## 1. Extract kernel infrastructure files

- [x] 1.1 Create `kernel/repo_base.py` — extract `TenantAwareRepositoryBase` from `kernel/tenant_institution/repos/base.py`; fix coupling: replace `self._model is not Client` with `hasattr(self._model, "client_id")` and DROP all imports from `kernel.tenant_institution.models` (Client, Institution, OrgUnit). Keep the `from kernel.tenant_context import TenantContext` import and `from kernel.db import Base` import.
- [x] 1.2 Create `kernel/audit.py` — extract `AuditEmitter` Protocol + `DefaultAuditEmitter` class from `kernel/tenant_institution/services/audit.py`. No imports from business.
- [x] 1.3 Create `kernel/transfer_coordinator.py` — extract `TransferCoordinator` Protocol + `DefaultTransferCoordinator` class from `kernel/tenant_institution/services/transfer.py`. No imports from business.
- [x] 1.4 Verify the 3 new kernel files import nothing from `kernel.tenant_institution` or `business` — grep to confirm A3 (kernel→∅) is satisfied at the file level.

## 2. Move domain code to business/tenant_institution/

- [x] 2.1 Create `backend/business/` directory (replacing `backend/modules/` placeholder); move `__init__.py` from `modules/` to `business/`.
- [x] 2.2 Remove `backend/modules/` directory.
- [x] 2.3 Create `business/tenant_institution/` directory with `__init__.py` (empty, matching original `kernel/tenant_institution/__init__.py`).
- [x] 2.4 Move `kernel/tenant_institution/models/` → `business/tenant_institution/models/` (6 files: __init__.py, approval.py, client.py, institution.py, institution_type.py, lifecycle.py, lookup.py, org_unit.py).
- [x] 2.5 Move `kernel/tenant_institution/repos/` → `business/tenant_institution/repos/` (5 files: __init__.py, approval_transfer_repo.py, client_repo.py, institution_repo.py, institution_type_repo.py, org_unit_repo.py). NOTE: `base.py` is NOT moved — it was extracted to `kernel/repo_base.py` in task 1.1. Delete the original `base.py`.
- [x] 2.6 Move `kernel/tenant_institution/routes/` → `business/tenant_institution/routes/` (3 files: __init__.py, platform.py, client_portal.py).
- [x] 2.7 Move `kernel/tenant_institution/services/` → `business/tenant_institution/services/` (5 files: __init__.py, dtos.py, service.py, state_machine.py, approval.py). NOTE: `audit.py` was extracted to `kernel/audit.py` (task 1.2) and `transfer.py` was extracted to `kernel/transfer_coordinator.py` (task 1.3). Delete the original `audit.py` and `transfer.py` from the moved directory.
- [x] 2.8 Move `kernel/tenant_institution/manifest.py` → `business/tenant_institution/manifest.py`.
- [x] 2.9 Move `kernel/tenant_institution/policies.py` → `business/tenant_institution/policies.py`.
- [x] 2.10 Move `kernel/tenant_institution/casbin_model.conf` → `business/tenant_institution/casbin_model.conf`.
- [x] 2.11 Move `kernel/tenant_institution/dependencies.py` → `business/tenant_institution/dependencies.py`.
- [x] 2.12 Move `kernel/tenant_institution/tests/__init__.py` → `business/tenant_institution/tests/__init__.py` (empty file).
- [x] 2.13 Remove the now-empty `kernel/tenant_institution/` directory (verify no files remain).

## 3. Update __init__.py re-exports

- [x] 3.1 Update `business/tenant_institution/repos/__init__.py` — change `TenantAwareRepositoryBase` import from `kernel.tenant_institution.repos.base` to `kernel.repo_base`. Keep all other repo imports but change `kernel.tenant_institution.repos` → `business.tenant_institution.repos`.
- [x] 3.2 Update `business/tenant_institution/services/__init__.py` — change `TransferCoordinator`/`DefaultTransferCoordinator` imports to `kernel.transfer_coordinator`; change `AuditEmitter`/`DefaultAuditEmitter` imports to `kernel.audit`; change all other service imports from `kernel.tenant_institution.services` → `business.tenant_institution.services`. Update `__all__` list accordingly.
- [x] 3.3 Update `business/tenant_institution/routes/__init__.py` — change imports from `kernel.tenant_institution.routes` → `business.tenant_institution.routes`.

## 4. Update domain-internal imports (business → kernel + business)

- [x] 4.1 Update `business/tenant_institution/repos/client_repo.py` — `from kernel.tenant_institution.repos.base import TenantAwareRepositoryBase` → `from kernel.repo_base import TenantAwareRepositoryBase`; update model imports from `kernel.tenant_institution.models` → `business.tenant_institution.models`.
- [x] 4.2 Update `business/tenant_institution/repos/institution_repo.py` — same pattern: repo_base from kernel, models from business.
- [x] 4.3 Update `business/tenant_institution/repos/institution_type_repo.py` — same pattern.
- [x] 4.4 Update `business/tenant_institution/repos/org_unit_repo.py` — same pattern.
- [x] 4.5 Update `business/tenant_institution/repos/approval_transfer_repo.py` — same pattern.
- [x] 4.6 Update `business/tenant_institution/services/service.py` — imports from `kernel.tenant_institution.services.audit` → `kernel.audit`; `kernel.tenant_institution.services.transfer` → `kernel.transfer_coordinator`; all other `kernel.tenant_institution` → `business.tenant_institution`.
- [x] 4.7 Update `business/tenant_institution/services/approval.py` — `kernel.tenant_institution` → `business.tenant_institution` for domain imports; `kernel.tenant_context` stays.
- [x] 4.8 Update `business/tenant_institution/routes/platform.py` — `kernel.tenant_institution` → `business.tenant_institution`; `kernel.tenant_context` stays.
- [x] 4.9 Update `business/tenant_institution/routes/client_portal.py` — same pattern.
- [x] 4.10 Update `business/tenant_institution/manifest.py` — `kernel.tenant_institution` → `business.tenant_institution`; `kernel.middleware` stays.
- [x] 4.11 Update `business/tenant_institution/dependencies.py` — `kernel.tenant_institution` → `business.tenant_institution`; `kernel.tenant_context` stays.
- [x] 4.12 Update `business/tenant_institution/models/__init__.py` — if it imports from `kernel.tenant_institution.models`, change to `business.tenant_institution.models`.

## 5. Update test imports

- [x] 5.1 Update `backend/tests/conftest.py` — `kernel.tenant_institution` → `business.tenant_institution` or `kernel` (for extracted pieces). `kernel.app_factory`, `kernel.tenant_context`, `kernel.middleware` stay.
- [x] 5.2 Update `backend/tests/test_api.py` — same pattern.
- [x] 5.3 Update `backend/tests/test_app_factory.py` — `kernel.tenant_institution` → `business.tenant_institution`.
- [x] 5.4 Update `backend/tests/test_audit_emission.py` — `kernel.tenant_institution.services.audit` → `kernel.audit`; other `kernel.tenant_institution` → `business.tenant_institution`.
- [x] 5.5 Update `backend/tests/test_casbin_permissions.py` — `kernel.tenant_institution` → `business.tenant_institution`.
- [x] 5.6 Update `backend/tests/test_configurable_enums.py` — same pattern.
- [x] 5.7 Update `backend/tests/test_field_purity.py` — same pattern.
- [x] 5.8 Update `backend/tests/test_import_contracts.py` — update contract test assertions to reflect new kernel files (repo_base, audit, transfer_coordinator) and business path (business.tenant_institution).
- [x] 5.9 Update `backend/tests/test_lifecycle.py` — `kernel.tenant_institution` → `business.tenant_institution`; `kernel.tenant_context` stays.
- [x] 5.10 Update `backend/tests/test_org_unit_hierarchy.py` — same pattern.
- [x] 5.11 Update `backend/tests/test_repos.py` — `kernel.tenant_institution.repos.base` → `kernel.repo_base`; other `kernel.tenant_institution` → `business.tenant_institution`.
- [x] 5.12 Update `backend/tests/test_rls.py` — same pattern.
- [x] 5.13 Update `backend/tests/test_template.py` — same pattern.
- [x] 5.14 Update `backend/tests/test_transfer.py` — `kernel.tenant_institution.services.transfer` → `kernel.transfer_coordinator`; other `kernel.tenant_institution` → `business.tenant_institution`.
- [x] 5.15 Update `backend/tests/test_uuid_pks.py` — same pattern.
- [x] 5.16 Update `backend/tests/test_boundary_declarations.py` — same pattern.

## 6. Update migration imports

- [x] 6.1 Update `backend/migrations/env.py` — `from kernel.db import Base` stays unchanged; if it imports `kernel.tenant_institution.models` for metadata loading, change to `business.tenant_institution.models`.

## 7. Update import-linter configuration

- [x] 7.1 Update `pyproject.toml` import-linter contracts: A3 `forbidden_modules` change `"modules"` → `"business"`; A4 `layers` add `"business"` after `"kernel"` to enforce the layer ordering (business → kernel allowed; kernel → business forbidden).
- [x] 7.2 Verify `root_packages` in import-linter config includes both `"kernel"` and `"business"`.

## 8. Verify — no regressions

- [x] 8.1 Run `python -m pytest backend/tests/ -v` — all 167 tests must pass with zero test-logic modifications (only import path changes).
- [x] 8.2 Run `lint-imports` — both contracts (A3 kernel→∅, A4 acyclic) must pass with the updated configuration.
- [x] 8.3 Grep-verify no remaining `kernel.tenant_institution` import paths exist anywhere in the codebase (except in archived OpenSpec changes or docs).
- [x] 8.4 Grep-verify `kernel/repo_base.py`, `kernel/audit.py`, `kernel/transfer_coordinator.py` import nothing from `business` or `kernel.tenant_institution`.
- [x] 8.5 Confirm `backend/modules/` no longer exists and `backend/business/` exists with `tenant_institution/` subdirectory.