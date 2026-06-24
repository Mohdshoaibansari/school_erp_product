## 1. Subscription Engine (C-07)

- [ ] 1.1 Define subscription data model: tier (free/paid), student_cap, billing_status, module_entitlements
- [ ] 1.2 Implement tenant-level subscription metadata on the tenant entity
- [ ] 1.3 Build subscription check API: `GET /api/subscription/status` returning tier, cap, current student count, available modules
- [ ] 1.4 Implement student count query: count active enrollments per tenant
- [ ] 1.5 Implement cap enforcement in student creation flow — reject with 402 if at cap
- [ ] 1.6 Implement bulk import cap enforcement — skip over-cap students, report count

## 2. Student Enrollment Lifecycle

- [ ] 2.1 Add lifecycle status field to enrollment: active, graduated, transferred, archived
- [ ] 2.2 Implement graduation flow: end-of-year process that transitions students to alumni
- [ ] 2.3 Implement transfer flow: move student between institutions with historical data preservation
- [ ] 2.4 Implement archival process: auto-archive students inactive for 2+ consecutive academic years
- [ ] 2.5 Build alumni read-only view — separate from active student management
- [ ] 2.6 Implement re-enrollment: create new active enrollment from archived alumni record

## 3. Module Gating — Backend

- [ ] 3.1 Define module registry: list of all modules with free/paid classification
- [ ] 3.2 Build subscription-checking middleware: `requireModule(moduleName)` — returns 403 if not entitled
- [ ] 3.3 Apply gating middleware to all paid module routes (Exams, Homework, Transport, Communication, Timetable)
- [ ] 3.4 Ensure 403 response does not reveal the module name or existence

## 4. Module Gating — Frontend

- [ ] 4.1 Add runtime endpoint `GET /api/modules/available` returning list of enabled modules for current tenant
- [ ] 4.2 Build navigation component that renders only available modules — no hidden placeholders
- [ ] 4.3 Configure frontend routing to redirect to dashboard on paid module URLs for free-tier users
- [ ] 4.4 Ensure paid module code is never rendered in free-tier view (lazy-load checking)

## 5. Integration & Validation

- [ ] 5.1 Write integration tests: free tier cap enforcement, module gating, student lifecycle transitions
- [ ] 5.2 Document the subscription model and billing counting rules in project README
- [ ] 5.3 Run `openspec validate school-erp-foundation --type change --strict`
