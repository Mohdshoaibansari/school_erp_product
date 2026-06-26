## Context

The School ERP needs three interconnected kernel services to provide the academic backbone for business modules (Attendance, Fees, Exams):

1. **Academic Structure Service** — Academic years, terms, grades, classes, sections
2. **Config & Rules Engine** — Typed configuration with scope inheritance and rule evaluation
3. **Calendar Service** — School day calendar for attendance and scheduling

These services are prerequisites for business modules that need to query academic structure, configuration rules, and calendar data.

### Existing ADRs in Force

- ADR-0004: Single multi-tenant deployment with row-level isolation — every table must include `tenant_id`
- ADR-0001: Soft-block student cap enforcement — 100 student limit for free tier

## Goals / Non-Goals

**Goals:**
- Implement academic hierarchy (Grade → Class → Section) using existing OrgUnit model
- Implement academic years and terms with auto-detection of current year/term
- Implement config with platform → client → institution inheritance
- Implement rules engine for module decision logic (attendance cutoff, late fee %)
- Implement calendar events (school_day, holiday, exam_day, event)

**Non-Goals:**
- No full scheduling/timetable system (future enhancement)
- No complex rule expressions (simple key-value config only)
- No calendar sync with external systems (Google Calendar, etc.)
- No multi-year academic planning (current year only for now)

## C4 Diagrams

### Level 1: System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                      School ERP System                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Academic     │  │  Config      │  │  Calendar    │         │
│  │  Service      │  │  Service     │  │  Service     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
         │                  │                   │
         ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL Database                        │
│  academic_years | terms | config_keys | config_values | events  │
└─────────────────────────────────────────────────────────────────┘
```

### Level 2: Container

```
┌─────────────────────────────────────────────────────────────────┐
│                    Express API Server                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Kernel Package                          │ │
│  │                                                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │ Academic      │  │ Config       │  │ Calendar     │   │ │
│  │  │ Service       │  │ Service      │  │ Service      │   │ │
│  │  │              │  │              │  │              │   │ │
│  │  │ • getCurrentYear │ • get       │  │ • getToday   │   │ │
│  │  │ • getCurrentTerm │ • set       │  │ • getDayType │   │ │
│  │  │ • getGrades  │  │ • createKey  │  │ • isHoliday  │   │ │
│  │  │ • getClasses │  │ • parseValue │  │ • getEvents  │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Level 3: Component (Academic Service)

```
┌─────────────────────────────────────────────────────────────────┐
│                    AcademicService                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Methods                                                   │   │
│  │  • createAcademicYear(institutionId, data)               │   │
│  │  • getCurrentYear(institutionId)                         │   │
│  │  • getAcademicYears(institutionId)                       │   │
│  │  • createTerm(data)                                      │   │
│  │  • getCurrentTerm(institutionId)                         │   │
│  │  • getGrades(institutionId)                              │   │
│  │  • getClasses(institutionId, gradeId?)                   │   │
│  │  • getSections(institutionId, classId?)                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ PrismaClient                                              │   │
│  │  • AcademicYear                                           │   │
│  │  • Term                                                   │   │
│  │  • OrgUnit (Grade/Class/Section)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Decisions

### Decision 1: Use OrgUnit for Grade/Class/Section

**Decision:** Reuse the existing `OrgUnit` model with types `GRADE`, `CLASS`, `SECTION` instead of creating separate tables.

**Rationale:**
- OrgUnit already supports hierarchical relationships (parentId)
- Consistent with institution structure (DIVISION, DEPARTMENT)
- Reduces schema complexity

**Consequences:**
- Grade, Class, Section are all OrgUnits with different types
- Queries filter by `type` field
- Hierarchy is self-referential via `parentId`

### Decision 2: Config Scope Inheritance

**Decision:** Config values inherit from platform → tenant → institution scope.

**Rationale:**
- Platform defaults work without configuration
- Institutions can override specific values
- Tenant-level config applies to all institutions in a tenant

**Consequences:**
- ConfigValue has nullable `tenantId` and `institutionId`
- Platform defaults: both null
- Tenant scope: `tenantId` set, `institutionId` null
- Institution scope: both set

### Decision 3: Calendar as Separate Service

**Decision:** Calendar events stored in dedicated `calendar_events` table, not as config values.

**Rationale:**
- Calendar has different query patterns (date range, type filtering)
- Calendar is institution-scoped, not hierarchical
- Calendar events are high-volume (365+ per year per institution)

**Consequences:**
- Separate `calendar_events` table with date index
- CalendarService independent of ConfigService
- Event types: SCHOOL_DAY, HOLIDAY, EXAM_DAY, EVENT

### Decision 4: Auto-Detection of Current Year/Term

**Decision:** Academic years and terms auto-detect "current" status based on today's date.

**Rationale:**
- Reduces manual configuration
- Always shows relevant data
- Supports overlapping terms (exam periods)

**Consequences:**
- `isCurrent` boolean on AcademicYear and Term
- Auto-set on create and query
- Manual override possible for edge cases

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| OrgUnit type confusion | Clear type enum, validation in service |
| Config inheritance complexity | Document scope precedence, test thoroughly |
| Calendar performance with many events | Date-based index, pagination |
| Auto-detection edge cases | Manual override via `isCurrent` flag |

## Open Questions

1. Should academic years be locked after completion? (Future: prevent edits)
2. Should calendar support recurring events? (Future: weekly patterns)
3. Should config support encrypted values? (Future: API keys, secrets)
