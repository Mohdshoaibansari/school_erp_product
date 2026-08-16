# Spec Delta — Configuration Framework (MODIFIED)

> **Change:** add-c05-academic-structure
> **Domain:** configuration-framework
> **Impact:** MODIFIED (new config keys)
> **Source:** `docs/architecture/adr-c05-academic-structure-implementation.md` (D7, D19)

---

## ADDED Requirements

### REQ-CONFIG-AC-01: Academic Template Config Keys

Add4 new config keys in the "Academic" category for C-05 template management.

| Key | Type | Default | Category | Module | Description |
|---|---|---|---|---|---|
| `academic.schoolTemplate` | json | (see below) | Academic | academic | Default academic structure template |
| `academic.cloneOnNewYear` | boolean | `true` | Academic | academic | Whether to clone from previous year |
| `academic.defaultSectionsPerClass` | number | `3` | Academic | academic | Default sections per class |
| `academic.defaultSubjects` | json | `["Mathematics","Science","English","Hindi","Social Studies","Computer Science"]` | Academic | academic | Default subjects for template |

**Default `academic.schoolTemplate` value:**
```json
{
  "gradeLevels": ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"],
  "sections": ["A", "B", "C"],
  "defaultSubjects": ["Mathematics", "Science", "English", "Hindi", "Social Studies", "Computer Science"],
  "termStructure": "yearly"
}
```

**Rules:**
- Config keys are seeded in Alembic migration (D7)
- Template excludes Room and Building (D19)
- Template is editable per client
