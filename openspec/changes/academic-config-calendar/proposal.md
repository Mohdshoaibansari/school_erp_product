## Why

The School ERP needs three interconnected kernel services that provide the academic backbone for business modules (Attendance, Fees, Exams):

1. **Academic Structure Service** — Academic years, terms, grades, classes, sections
2. **Config & Rules Engine** — Typed configuration with scope inheritance and rule evaluation
3. **Calendar Service** — School day calendar for attendance and scheduling

Without these services, business modules cannot query academic structure, configuration rules, or calendar data.

## What Changes

- Implement academic hierarchy (Grade → Class → Section) using existing OrgUnit model
- Implement academic years and terms with auto-detection of current year/term
- Implement config with platform → client → institution inheritance
- Implement rules engine for module decision logic (attendance cutoff, late fee %)
- Implement calendar events (school_day, holiday, exam_day, event)

## Capabilities

### New Capabilities

- `academic-structure`: Academic years, terms, grades, classes, sections hierarchy
- `config-rules-engine`: Typed configuration with scope inheritance and rule evaluation
- `calendar-service`: School day calendar for attendance and scheduling

### Modified Capabilities

- None

## Impact

- **Packages affected**: `packages/database/prisma/schema.prisma`, `packages/kernel/src/academic/`, `packages/kernel/src/config/`, `packages/kernel/src/calendar/`
- **Dependencies**: Requires completed kernel services (Tenant, Institution, Users)
- **Required by**: Business modules (Attendance, Fees, Exams)
- **Database**: New tables for academic_years, terms, subjects, config_keys, config_values, calendar_events
- **API**: New endpoints for academic structure, config management, calendar queries
