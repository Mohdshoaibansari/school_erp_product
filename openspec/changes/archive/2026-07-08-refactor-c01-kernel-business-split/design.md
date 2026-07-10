## Context

C-01 (Tenant & Institution Management) is the first implemented capability. During the code walkthrough it was discovered that `kernel/tenant_institution/` bundles two distinct concerns:

1. **Kernel infrastructure** — services every business module must import: `TenantAwareRepositoryBase`, `AuditEmitter` Protocol, `TransferCoordinator` Protocol. Today these live inside `kernel/tenant_institution/repos/base.py` and `kernel/tenant_institution/services/audit.py` / `transfer.py`, making them part of a business package. Future modules (Attendance, Fees, etc.) would need to `import kernel.tenant_institution...` — importing from a sibling business module, which is the wrong dependency direction.

2. **Business domain** — logic only C-01's own workflows need: Client/Institution/OrgUnit lifecycle state machines, InstitutionType template materialization, ownership transfer workflow, D11 Casbin permission matrix.

Additionally, `TenantAwareRepositoryBase` (line ~22 of `kernel/tenant_institution/repos/base.py`) imports `from kernel.tenant_institution.models import Client, Institution, OrgUnit` and uses `self._model is not Client` for the `_is_client_scoped` check. This couples the kernel base to a business model, violating A3 (kernel → ∅). `Institution` and `OrgUnit` imports are dead/unused.

The architecture decisions have already been recorded in `docs/` (commit `1d08da2`):
- `docs/platform-capabilities/platform-capabilities-v3.md` — Appendix A: C-01a + C-01b rows, §5.1 Infrastructure vs. Domain
- `docs/architecture/adr-platform-software-architecture.md` — A2 consumed-by-all rule, §4 model diagram
- `docs/platform-capabilities/c-01-tenant-institution-explained.md` — v1.1 note
- `docs/business-modules/README.md` — business module catalog

Current state: 167 tests passing, import-linter 2 contracts (A3 kernel→∅, A4 acyclic), single Alembic migration `001_c01_initial.py`.

## Goals / Non-Goals

**Goals:**
- Extract `TenantAwareRepositoryBase`, `AuditEmitter`, `TransferCoordinator` to flat `kernel/` files so every future business module imports from `kernel/`, not from a sibling business package.
- Move all C-01 domain logic to `business/tenant_institution/` so the business tier is visually and structurally separate from kernel.
- Fix the `TenantAwareRepositoryBase` → `Client` model coupling so `kernel/` imports nothing from business (A3 compliance).
- Rename `backend/modules/` → `backend/business/` (placeholder + docs already updated).
- All 167 tests pass with **zero test-logic modifications** (only import paths change).

**Non-Goals:**
- No behavioral changes to C-01 APIs, data models, or business logic.
- No new features or capabilities.
- No database migration changes.
- No splitting of other capabilities (C-02..C-06, C-11) — they are footnoted for future splits.
- No frontend changes.

## Decisions

### D1: Kernel rule = "consumed-by-all"

**Decision:** Kernel = any service/entity/Protocol that EVERY business module MUST import or depend on. Business = domain logic only its own workflows use.

**Rationale:** The original A2 used "dependency depth" as the tier rule, which was too vague. "Consumed-by-all" is precise: if every module needs it, it's kernel; if only the owning capability needs it, it's business. This directly determines what gets extracted.

**Alternatives considered:**
- "Dependency depth" (original A2) — vague; doesn't distinguish infrastructure within a capability from its domain logic.
- "Build order" — conflates when something is built with what tier it belongs to.

### D2: Kernel infrastructure location = flat under `kernel/`

**Decision:** Each extracted kernel piece gets its own file directly under `kernel/` — `kernel/repo_base.py`, `kernel/audit.py`, `kernel/transfer_coordinator.py` — mirroring how `tenant_context.py` and `middleware.py` already live at `kernel/`.

**Rationale:** Flat layout is simpler than nested packages for infrastructure pieces. Each piece is a single file with a single concern. No subdirectory nesting needed.

**Alternatives considered:**
- `kernel/infrastructure/` subdirectory — adds unnecessary nesting for 3 files.
- `kernel/tenant/` namespace — would re-introduce the concept of a tenant sub-package inside kernel.

### D3: C-01 domain location = `business/tenant_institution/`

**Decision:** All C-01 domain logic moves to `business/tenant_institution/` — mirroring the planned structure for future modules (`business/attendance/`, `business/fees/`, etc.).

**Rationale:** Semantic package name matching the capability name. Consistent with the `business/` tier naming. Import paths become `from business.tenant_institution.services import ...`.

**Alternatives considered:**
- `business/c01/` — uses capability ID, less descriptive.
- Keep at `kernel/tenant_institution/` — conceptually wrong (domain logic labeled kernel).

### D4: Rename `modules/` → `business/` everywhere

**Decision:** Rename the directory `backend/modules/` → `backend/business/`. Update all references in docs, ADR, and code.

**Rationale:** The architecture ADR originally called the business tier "modules/". The chosen path is `business/`. One consistent name everywhere — the tier name matches the directory name.

### D5: C-01 in capability matrix = C-01a + C-01b

**Decision:** Replace the single C-01 row in the Classification Matrix with two rows: C-01a (Tenant Identity Infrastructure, Kernel) and C-01b (Tenant & Institution Domain, Business).

**Rationale:** Explicitly records that C-01 produces two artifacts: kernel packages (consumed by all) and a business module (consumed only by C-01 workflows). C-01a and C-01b share the same migration and are developed together, but the split ensures future modules import only infrastructure, not domain logic.

### D6: Other Kernel capabilities = footnote, not pre-split

**Decision:** C-02..C-06, C-11 are marked `Kernel*` in the matrix with a footnote: "will be split into a/b rows when built, following the C-01 precedent." Not pre-split now.

**Rationale:** We don't know the exact infrastructure-vs-domain split for unbuilt capabilities. Pre-splitting would be speculative. The footnote records the pattern so it's not forgotten.

### D7: Platform Kernel = all of Phase 1 (build order)

**Decision:** The Platform Kernel includes all Phase 1 capabilities — both infrastructure (C-01a) and domain (C-01b). "Kernel" in this context means "build order, not dependency depth."

**Rationale:** C-01b is a business module that must exist before any other business module can function (it owns the Client/Institution tables). Excluding it from "Platform Kernel" would imply it can be built later, which is false.

### D8: `docs/business-modules/` folder

**Decision:** Create `docs/business-modules/` with a README listing business modules (C-01b first). Future explained docs go here.

**Rationale:** Provides a parallel to `docs/platform-capabilities/` for business module documentation.

## File Extraction Plan

### EXTRACT (kernel/tenant_institution/ → kernel/)

| New file | Source | What moves |
|---|---|---|
| `kernel/repo_base.py` | `kernel/tenant_institution/repos/base.py` | `TenantAwareRepositoryBase` class |
| `kernel/audit.py` | `kernel/tenant_institution/services/audit.py` | `AuditEmitter` Protocol + `DefaultAuditEmitter` class |
| `kernel/transfer_coordinator.py` | `kernel/tenant_institution/services/transfer.py` | `TransferCoordinator` Protocol + `DefaultTransferCoordinator` class |

### MOVE (domain → business/)

| Source | Destination | What moves |
|---|---|---|
| `kernel/tenant_institution/` (all remaining files) | `business/tenant_institution/` | models/, repos/ (minus base.py), routes/, services/ (minus audit.py + transfer.py), manifest.py, policies.py, casbin_model.conf, dependencies.py |
| `backend/modules/` | `backend/business/` | Placeholder directory rename |

### CRITICAL COUPLING FIX

`kernel/tenant_institution/repos/base.py` line ~22:
```python
from kernel.tenant_institution.models import Client, Institution, OrgUnit
```
Used only for: `self._model is not Client` (the `_is_client_scoped` check). `Institution` and `OrgUnit` imports are dead/unused.

**Fix in extracted `kernel/repo_base.py`:**
```python
# BEFORE (coupled to business model):
from kernel.tenant_institution.models import Client, Institution, OrgUnit
...
if self._model is not Client:

# AFTER (no business import):
# NO import from business models
...
if hasattr(self._model, "client_id"):
```

After the fix, `kernel/repo_base.py` imports NOTHING from business — satisfying A3 (kernel → ∅). The `hasattr` check is semantically equivalent: models with `client_id` are client-scoped, models without it (like `Client` itself) are not.

## Risks / Trade-offs

- **[Risk] Test import breakage** → All 167 tests reference `kernel.tenant_institution` paths. Import-only changes are mechanical but error-prone. → **Mitigation:** Update imports file-by-file, run tests after each batch, NOT all at once. The 167 tests must pass with zero test-logic changes.

- **[Risk] Circular imports after extraction** → `kernel/audit.py` or `kernel/transfer_coordinator.py` might indirectly reference business types. → **Mitigation:** Both Protocols are defined with `typing.Protocol` and have no runtime imports from business. `DefaultAuditEmitter` and `DefaultTransferCoordinator` are no-op stubs. Verify with `lint-imports` after extraction.

- **[Risk] `hasattr` check语义变化** → Replacing `is not Client` with `hasattr(self._model, "client_id")` could behave differently if a non-client model has a `client_id` column. → **Mitigation:** `Client` is the ONLY model without `client_id` in C-01's schema. All other models (Institution, OrgUnit, InstitutionType, lifecycle event tables) carry `client_id`. The `hasattr` check is equivalent.

- **[Trade-off] Large mechanical diff** → Moving ~38 files' import paths produces a large diff that's hard to review line-by-line. → **Mitigation:** The diff is purely import-path changes. Use `git diff --stat` for the overview and spot-check individual files. Behavior is proven unchanged by the 167 passing tests.