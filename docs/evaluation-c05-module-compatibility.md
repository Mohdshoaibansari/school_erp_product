# Evaluation — C-05 Academic Structure Module Compatibility

> **Date:** 2026-08-16
> **Status:** ACTION REQUIRED

---

## Summary

Migration 021 adds FK columns to `homework` and `fee_assignment` tables, but the **models, repos, DTOs, routes, and services** still reference the old free-text columns. After migration 021 runs, the old columns are dropped and the code will break.

---

## Module Status

| Module | Status | Action Required |
|---|---|---|
| C-01 Tenant & Institution | ✅ Compatible | None — has C-05 boundary hook for ownership transfer |
| C-02 Identity & User | ✅ Compatible | None |
| C-03 Authentication | ✅ Compatible | None |
| C-04 Authorization | ✅ Compatible | 10 new permissions already added in migration 020 |
| C-05 Academic Structure | ✅ Implemented | None |
| C-08 Configuration | ✅ Compatible | 4 academic config keys already added in migration 020 |
| **Homework** | ❌ **BROKEN** | Models, repos, DTOs, routes, services need FK migration |
| **Fees** | ❌ **BROKEN** | Models, repos, DTOs, routes, services need FK migration |

---

## Homework Module — Required Changes

### Current State (BROKEN)
```python
# models/homework_models.py
subject = Column(Text)        # ← DROPPED by migration 021
grade_level = Column(Text)    # ← DROPPED by migration 021
section = Column(Text)        # ← DROPPED by migration 021
```

### Required State
```python
# models/homework_models.py
subject_id = Column(UUID, ForeignKey("subject.id"))
grade_level_id = Column(UUID, ForeignKey("grade_level.id"))
section_id = Column(UUID, ForeignKey("section.id"))
```

### Files to Update

| File | Changes |
|---|---|
| `models/homework_models.py` | Replace text columns with FK columns |
| `repos/homework_repos.py` | Update create/list_filtered to use FK fields |
| `services/dtos.py` | Replace text fields with UUID fields |
| `services/service.py` | Update create/list to use FK fields |
| `routes/homework_routes.py` | Update query params from text to UUID |

---

## Fees Module — Required Changes

### Current State (BROKEN)
```python
# models/fee_models.py
academic_term = Column(Text)  # ← DROPPED by migration 021
```

### Required State
```python
# models/fee_models.py
term_id = Column(UUID, ForeignKey("term.id"))
```

### Files to Update

| File | Changes |
|---|---|
| `models/fee_models.py` | Replace text column with FK column |
| `repos/fee_repos.py` | Update create/list to use FK field |
| `services/dtos.py` | Replace text field with UUID field |
| `services/service.py` | Update create to use FK field |
| `routes/fee_assignments.py` | Update query params |

---

## Effort Estimate

| Module | Effort |
|---|---|
| Homework module | ~2 hours (5 files) |
| Fees module | ~1 hour (5 files) |
| **Total** | **~3 hours** |

---

## Risk

If migration 021 runs before the code is updated:
- All homework/fee API calls will fail with 500 errors
- The old text columns will be dropped, so rollback requires re-adding them

**Recommendation:** Update the code BEFORE running migration 021, or revert migration 021 and re-run it after code updates.
