# Impact Classification — C-05 Academic Structure Framework (Enhanced)

> **Capability:** C-05 Academic Structure Framework
> **Status:** Draft
> **Last updated:** 2026-09-02
> **Source:** `docs/prd/C-05-Academic-Structure-enhanced.md`, grill session 2026-09-02
> **Supersedes:** Previous impact classification (2026-08-14)

---

## 1. Impact Summary

C-05 is a **refactored kernel capability** that introduces permanent academic masters, year-specific configuration through ClassAcademicYear, and curriculum versioning. This is a greenfield implementation — no production data to preserve.

| Impact Type | Count |
|---|---|
| **ADDED** (new tables) | 5 new tables |
| **MODIFIED** (existing tables) | 6 tables modified |
| **REMOVED** (deprecated tables) | 4 tables removed |
| **CROSS-CUTTING** (multiple domains) | 2 capabilities affected |

---

## 2. Key Design Decisions (from Grill Session)

| # | Decision | Rationale |
|---|---|---|
| D1 | GradeLevel has `org_unit_id` FK | Links academic grades to organizational units (Primary/Secondary) |
| D2 | ClassAcademicYear auto-created at AcademicYear creation only | New Classes not auto-added to existing Planning years |
| D3 | `grade_academic_year_curriculum` bridge table | One CurriculumVersion per Grade per AcademicYear |
| D4 | Section has `class_academic_year_id` (not `academic_year_id`) | Section belongs to ClassAcademicYear |
| D5 | Subject belongs to CurriculumVersion | Not a standalone master |
| D6 | SectionSubject has `is_active` flag | Supports disable without delete |
| D7 | Remove TeacherAssignment, StudentEnrollment | Deferred to Teacher/Student modules |
| D8 | Remove SubjectGroup, SubjectGroupMember | Replaced by Curriculum/CurriculumVersion |
| D9 | AcademicYear lifecycle: planning → active → closed + cancelled | Cancelled is terminal for Planning years |
| D10 | Term status computed dynamically | No `status` column |
| D11 | ClassAcademicYear has no independent lifecycle | Derived from AcademicYear |
| D12 | Section mutability tracked with `created_at` | Distinguish existing vs new sections during Active year |
| D13 | CurriculumVersion immutability at app level | No update API |
| D14 | Early closure with `closed_at` timestamp | Preserves planned end_date |
| D15 | Greenfield implementation | No data migration needed |
| D16 | Remove all C-05 config keys | Permanent masters are admin-driven |
| D17 | Skip Homework/FeeAssignment changes | Rebuild those modules separately |

---

## 3. Table Changes

### 3.1 Tables to MODIFY (6)

#### `academic_year`

| Column | Change | Notes |
|---|---|---|
| `status` | Add `cancelled` value | Terminal state for Planning years |
| `closed_at` | ADD (nullable timestamp) | Actual closure timestamp for early closure |

#### `term`

| Column | Change | Notes |
|---|---|---|
| `status` | REMOVE | Status computed dynamically from dates |

#### `grade_level`

| Column | Change | Notes |
|---|---|---|
| `academic_year_id` | REMOVE | GradeLevel is a permanent master |
| `org_unit_id` | ADD (FK to `org_unit.id`) | Links to organizational unit |

#### `class`

| Column | Change | Notes |
|---|---|---|
| `academic_year_id` | REMOVE | Class is a permanent master |

#### `section`

| Column | Change | Notes |
|---|---|---|
| `academic_year_id` | REMOVE | Section belongs to ClassAcademicYear |
| `class_academic_year_id` | ADD (FK to `class_academic_year.id`) | Year-specific parent |

#### `subject`

| Column | Change | Notes |
|---|---|---|
| `academic_year_id` | REMOVE | Subject belongs to CurriculumVersion |
| `curriculum_version_id` | ADD (FK to `curriculum_version.id`) | Curriculum ownership |

### 3.2 Tables to REMOVE (4)

| Table | Reason |
|---|---|
| `subject_group` | Replaced by Curriculum/CurriculumVersion |
| `subject_group_member` | Replaced by Curriculum/CurriculumVersion |
| `teacher_assignment` | Deferred to Teacher module |
| `student_enrollment` | Deferred to Student module |

### 3.3 Tables to CREATE (5)

#### `class_academic_year`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `client_id` | UUID | FK to `client.id` |
| `institution_id` | UUID | FK to `institution.id` |
| `class_id` | UUID | FK to `class.id` |
| `academic_year_id` | UUID | FK to `academic_year.id` |
| `offered` | BOOLEAN | Whether class is offered this year |
| `created_at` | TIMESTAMP | Audit |
| `updated_at` | TIMESTAMP | Audit |

**Constraints:** Unique(`class_id`, `academic_year_id`)

#### `curriculum`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `client_id` | UUID | FK to `client.id` |
| `institution_id` | UUID | FK to `institution.id` |
| `grade_level_id` | UUID | FK to `grade_level.id` |
| `name` | VARCHAR(100) | e.g., "Grade 11 Curriculum" |
| `created_at` | TIMESTAMP | Audit |
| `updated_at` | TIMESTAMP | Audit |

#### `curriculum_version`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `client_id` | UUID | FK to `client.id` |
| `institution_id` | UUID | FK to `institution.id` |
| `curriculum_id` | UUID | FK to `curriculum.id` |
| `version_number` | INTEGER | e.g., 1, 2, 3 |
| `name` | VARCHAR(100) | e.g., "V1", "V2" |
| `created_at` | TIMESTAMP | Audit |
| `updated_at` | TIMESTAMP | Audit |

**Constraints:** Unique(`curriculum_id`, `version_number`)

#### `section_subject`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `client_id` | UUID | FK to `client.id` |
| `institution_id` | UUID | FK to `institution.id` |
| `section_id` | UUID | FK to `section.id` |
| `subject_id` | UUID | FK to `subject.id` |
| `is_active` | BOOLEAN | Default true |
| `created_at` | TIMESTAMP | Audit |

**Constraints:** Unique(`section_id`, `subject_id`)

#### `grade_academic_year_curriculum`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `client_id` | UUID | FK to `client.id` |
| `institution_id` | UUID | FK to `institution.id` |
| `grade_level_id` | UUID | FK to `grade_level.id` |
| `academic_year_id` | UUID | FK to `academic_year.id` |
| `curriculum_version_id` | UUID | FK to `curriculum_version.id` |
| `created_at` | TIMESTAMP | Audit |

**Constraints:** Unique(`grade_level_id`, `academic_year_id`)

---

## 4. Entity Relationship Summary

```
C-01 OrgUnit
      │
      ▼
C-05 GradeLevel (permanent master)
      │
      ├── Curriculum
      │     └── CurriculumVersion
      │           └── Subject
      │
      └── Class (permanent master)
            └── ClassAcademicYear (year-specific)
                  └── Section (year-specific)
                        └── SectionSubject

AcademicYear
   ├── Term
   └── ClassAcademicYear

GradeLevel + AcademicYear
   └── GradeAcademicYearCurriculum → CurriculumVersion
```

---

## 5. Business Invariants

| # | Invariant | Enforcement |
|---|---|---|
| 1 | GradeLevel.institution_id must match OrgUnit.institution_id | App level |
| 2 | No overlapping AcademicYears within an Institution | DB constraint |
| 3 | At most one Active AcademicYear per Institution | App level |
| 4 | Current Active year must be explicitly closed before another becomes Active | App level |
| 5 | Terms must be contained within AcademicYear and cannot overlap | App level |
| 6 | ClassAcademicYear uniqueness: one per Class + AcademicYear | DB constraint |
| 7 | Section belongs to exactly one ClassAcademicYear | DB constraint |
| 8 | ClassAcademicYear.offered = false → Section count = 0 | App level |
| 9 | SectionSubject must reference Subject from applicable Grade CurriculumVersion | App level |
| 10 | Closed AcademicYears immutable through normal operations | App level |
| 11 | CurriculumVersion immutable once created | App level (no update API) |
| 12 | Section identity immutable once AcademicYear is Active | App level |
| 13 | One CurriculumVersion per Grade per AcademicYear | DB constraint |

---

## 6. New Permissions (C-04)

| Permission | Description | Default Roles |
|---|---|---|
| `academic_year.create` | Create academic year | Admin, institution_admin |
| `academic_year.read` | Read academic year | All roles |
| `academic_year.update` | Update academic year | Admin, institution_admin |
| `academic_year.transition` | Transition lifecycle | Admin, institution_admin |
| `class_academic_year.create` | Create class-academic year link | Admin, institution_admin |
| `class_academic_year.read` | Read class-academic year | All roles |
| `class_academic_year.update` | Update class-academic year | Admin, institution_admin |
| `section.create` | Create section | Admin, institution_admin |
| `section.read` | Read section | All roles |
| `section.update` | Update section | Admin, institution_admin |
| `section.delete` | Delete section (Planning only) | Admin, institution_admin |
| `curriculum.create` | Create curriculum | Admin, institution_admin |
| `curriculum.read` | Read curriculum | All roles |
| `curriculum.update` | Update curriculum | Admin, institution_admin |
| `curriculum_version.create` | Create curriculum version | Admin, institution_admin |
| `curriculum_version.read` | Read curriculum version | All roles |
| `section_subject.create` | Assign subject to section | Admin, institution_admin |
| `section_subject.read` | Read section subjects | All roles |
| `section_subject.update` | Update section subject | Admin, institution_admin |

---

## 7. RLS Policies

All C-05 tables carry `client_id` and `institution_id` for tenant isolation:

```sql
-- Same pattern as existing tables
CREATE POLICY <table>_sel ON <table> FOR SELECT USING (
  is_platform_owner() OR client_id = current_client_id()
);
CREATE POLICY <table>_ins ON <table> FOR INSERT WITH CHECK (
  is_platform_owner() OR client_id = current_client_id()
);
-- ... (same for all C-05 tables)
```

Tables: `academic_year`, `term`, `grade_level`, `class`, `class_academic_year`, `section`, `curriculum`, `curriculum_version`, `subject`, `section_subject`, `grade_academic_year_curriculum`

---

## 8. Cross-Cutting Impacts

### 8.1 Authorization (C-04)

| Impact | Details |
|---|---|
| New permissions | 19 new permissions for academic structure management |
| Role assignments | Admin and institution_admin get academic permissions |
| Casbin policies | New policies for academic entities |

### 8.2 Tenant & Institution (C-01)

| Impact | Details |
|---|---|
| No schema changes | C-01 tables unchanged |
| GradeLevel references OrgUnit | New `org_unit_id` FK on `grade_level` |

### 8.3 Identity & User (C-02)

| Impact | Details |
|---|---|
| No schema changes | C-02 tables unchanged |
| Teacher/Student references deferred | Will be addressed when those modules are rebuilt |

---

## 9. Migration Plan

### 9.1 Alembic Migration

Since this is a greenfield implementation:

1. Drop existing C-05 tables (or rename for backup)
2. Create new C-05 tables (11 tables)
3. Seed permissions in `permission` and `role_permission`
4. Add RLS policies for all C-05 tables

### 9.2 Rollback Plan

- New tables are new — drop on rollback
- Permissions are soft-deleted on rollback

---

## 10. Testing Strategy

| Test Type | Scope |
|---|---|
| Unit tests | C-05 services (lifecycle transitions, SectionSubject validation) |
| Integration tests | ClassAcademicYear auto-creation, CurriculumVersion assignment |
| Authorization tests | All 19 new permissions, role coverage |
| Invariant tests | Business rules (overlap, uniqueness, immutability) |

---

## 11. Effort Estimate

| Component | Estimate |
|---|---|
| C-05 models + repos | 2 days |
| C-05 services (lifecycle, validation) | 3 days |
| C-05 routes + DTOs | 2 days |
| C-05 permissions + RLS | 1 day |
| Tests | 2 days |
| Documentation + verification | 1 day |
| **Total** | **~11 days** |

---

## 12. Deferred Items

The following are explicitly out of scope for this iteration:

| Item | Reason |
|---|---|
| TeacherAssignment | Deferred to Teacher module |
| StudentEnrollment | Deferred to Student module |
| Homework FK references | Will rebuild when Homework module is addressed |
| FeeAssignment FK references | Will rebuild when Fee module is addressed |
| College/University model | Future scope |
| Config keys | Not needed with permanent masters |
