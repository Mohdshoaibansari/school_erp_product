## Proposal: Academic Structure, Config & Rules Engine, Calendar Service

### Summary
Implement three interconnected kernel services that provide the academic backbone for the School ERP:
1. **Academic Structure Service** — Academic years, terms, grades, classes, sections
2. **Config & Rules Engine** — Typed configuration with scope inheritance and rule evaluation
3. **Calendar Service** — School day calendar for attendance and scheduling

### Motivation
These services are prerequisites for business modules (Attendance, Fees, Exams) that need to query academic structure, configuration rules, and calendar data.

### Scope
- Academic hierarchy (Grade → Class → Section)
- Academic years and terms with auto-detection
- Config with platform → client → institution inheritance
- Rules engine for module decision logic
- Calendar events (school_day, holiday, exam_day, event)

### Dependencies
- Requires completed kernel services (Tenant, Institution, Users)
- Required by business modules (Attendance, Fees, Exams)
