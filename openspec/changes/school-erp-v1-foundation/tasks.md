## 1. Project Scaffold

- [x] 1.1 Initialize root `package.json` with pnpm workspace configuration
- [x] 1.2 Create `pnpm-workspace.yaml` listing `packages/*` and `apps/*`
- [x] 1.3 Create `tsconfig.base.json` with shared TypeScript compiler options
- [x] 1.4 Create `.env.example` with Supabase URL, anon key, and service role key
- [x] 1.5 Create `.gitignore` for Node.js, Prisma, and environment files

## 2. Database Package (`packages/database`)

- [x] 2.1 Scaffold `packages/database/package.json` with `@school-erp/database` name and Prisma dependency
- [x] 2.2 Define Prisma schema with `tenants`, `users`, `user_tenants`, and `user_roles` tables
- [x] 2.3 Define `level_definitions`, `level_instances`, and `subjects` tables for academic structure
- [x] 2.4 Define `class_teachers` and `subject_teachers` junction tables for authorization
- [x] 2.5 Define `students`, `student_parents`, and `student_enrollments` tables
- [x] 2.6 Define `attendance_records`, `fee_structures`, `fee_payments`, and `fee_receipts` tables
- [x] 2.7 Define `timetable_entries`, `exam_schedules`, `exam_marks`, and `report_cards` tables
- [x] 2.8 Define `tenant_modules` and `academic_years` tables
- [x] 2.9 Add `tenant_id`, `created_at`, `updated_at`, `created_by`, `deleted_at` columns to all tenant-scoped tables
- [ ] 2.10 Create initial Prisma migration and generate Prisma client
- [ ] 2.11 Write raw SQL migration for Row Level Security policies (tenant isolation)

## 3. Shared Package (`packages/shared`)

- [x] 3.1 Scaffold `packages/shared/package.json` with `@school-erp/shared` name
- [x] 3.2 Define shared TypeScript types: `PaginatedResult<T>`, `AcademicLevel`, `UserRole`, `ModuleName`
- [x] 3.3 Create custom error classes: `NotFoundError`, `ValidationError`, `StudentLimitExceededError`, `ModuleNotEnabledError`
- [x] 3.4 Implement pagination helpers: `paginate()`, `PaginatedResult<T>`
- [x] 3.5 Implement common validators: email, phone, required field, date range
- [x] 3.6 Implement ID generation utilities: admission numbers, fee receipt numbers

## 4. Kernel: Tenant & Identity Services

- [x] 4.1 Scaffold `packages/kernel/package.json` with `@school-erp/kernel` name and dependencies on shared + database
- [x] 4.2 Implement `TenantService` with create tenant, resolve by subdomain, update status (activate/suspend/archive)
- [x] 4.3 Implement `IdentityService` with create user, assign role, invite staff, suspend user
- [x] 4.4 Implement Supabase Auth admin integration for user creation and invitation emails
- [x] 4.5 Export kernel services from `packages/kernel/src/index.ts`

## 5. Kernel: Academic Structure Service

- [x] 5.1 Implement `AcademicService` with level definition CRUD (per tenant)
- [x] 5.2 Implement level instance tree management (create/update/delete with parent-child relationships)
- [x] 5.3 Implement subject catalog CRUD (per tenant)
- [x] 5.4 Implement academic year management (create, activate, complete)
- [x] 5.5 Implement teacher assignment: class teacher (`class_teachers`) and subject teacher (`subject_teachers`)
- [x] 5.6 Implement student-to-level placement and promotion across academic years

## 6. Kernel: Authorization Service

- [x] 6.1 Implement `AuthorizationService` with role-to-permission mapping
- [x] 6.2 Implement `checkPermission(userId, tenantId, permission)` for RBAC gate
- [x] 6.3 Implement `getClassTeacherScope(teacherId)` returning assigned level instances
- [x] 6.4 Implement `getSubjectTeacherScope(teacherId, subjectId)` returning assigned classes
- [x] 6.5 Export authorization service from kernel index

## 7. Kernel: Subscription Service

- [x] 7.1 Implement `SubscriptionService` with module enable/disable per tenant
- [x] 7.2 Implement `isModuleEnabled(tenantId, moduleName)` check
- [x] 7.3 Implement student limit enforcement: `checkStudentLimit(tenantId)` throwing `StudentLimitExceededError` at cap
- [x] 7.4 Implement free tier assignment on tenant creation (Students, Attendance, Fees enabled, 100-student cap)
- [x] 7.5 Export subscription service from kernel index

## 8. Module: Student Management (`packages/students`)

- [x] 8.1 Scaffold `packages/students/package.json` with `@school-erp/students` name, depends on kernel + shared
- [x] 8.2 Implement `StudentService` with create student (manual entry with validation and limit check)
- [x] 8.3 Implement bulk CSV import with row-level error reporting
- [x] 8.4 Implement student profile update and guardian information management
- [x] 8.5 Implement bulk promotion: select source class, destination class, pick students per academic year
- [x] 8.6 Implement student status management (active, transferred, graduated, archived)

## 9. Module: Attendance (`packages/attendance`)

- [x] 9.1 Scaffold `packages/attendance/package.json` with `@school-erp/attendance` name
- [x] 9.2 Implement `AttendanceService` with mark attendance (scope-filtered to class teacher's sections)
- [x] 9.3 Implement bulk "mark all present" with individual overrides
- [x] 9.4 Implement view existing attendance by date and section
- [x] 9.5 Implement attendance reports: section-level daily summary, monthly grid

## 10. Module: Fee Management (`packages/fees`)

- [x] 10.1 Scaffold `packages/fees/package.json` with `@school-erp/fees` name
- [x] 10.2 Implement `FeeService` with fee structure CRUD per class and academic year
- [x] 10.3 Implement fee collection recording (full and partial payments)
- [x] 10.4 Implement receipt generation with unique receipt numbers
- [x] 10.5 Implement pending dues report per class with outstanding balances

## 11. Module: Timetable (`packages/timetable`)

- [x] 11.1 Scaffold `packages/timetable/package.json` with `@school-erp/timetable` name
- [x] 11.2 Implement `TimetableService` with weekly grid CRUD per section
- [x] 11.3 Implement teacher conflict detection when assigning overlapping slots
- [x] 11.4 Implement teacher's personal timetable view (all assigned periods across sections)
- [x] 11.5 Add module gating check — reject requests if timetable module not enabled for tenant

## 12. Module: Exams & Grades (`packages/exams`)

- [x] 12.1 Scaffold `packages/exams/package.json` with `@school-erp/exams` name
- [x] 12.2 Implement `ExamService` with exam schedule CRUD (exam name, subjects, dates, classes)
- [x] 12.3 Implement marks entry with scope-filtering (subject teacher sees only assigned classes and subject)
- [x] 12.4 Implement mark validation (max marks enforcement)
- [x] 12.5 Implement report card generation per student per exam
- [x] 12.6 Add module gating check — reject requests if exams module not enabled for tenant

## 13. API Server (`apps/api`)

- [x] 13.1 Scaffold `apps/api/package.json` with Fastify, `@fastify/swagger`, `@supabase/supabase-js` dependencies
- [x] 13.2 Implement tenant resolution middleware (extract subdomain, resolve tenantId)
- [x] 13.3 Implement Supabase JWT validation middleware (verify session, extract userId)
- [x] 13.4 Implement authorization middleware (check role permission, inject scope context)
- [x] 13.5 Implement module gating middleware (reject if module not enabled)
- [x] 13.6 Implement global error handler (map custom errors to HTTP status codes)
- [x] 13.7 Create route handlers for Student Management endpoints with OpenAPI schemas
- [x] 13.8 Create route handlers for Attendance endpoints with OpenAPI schemas
- [x] 13.9 Create route handlers for Fee Management endpoints with OpenAPI schemas
- [x] 13.10 Create route handlers for Timetable endpoints with OpenAPI schemas
- [x] 13.11 Create route handlers for Exams & Grades endpoints with OpenAPI schemas
- [x] 13.12 Create route handlers for admin endpoints: tenant config, module management, user management
- [x] 13.13 Configure `@fastify/swagger` with OpenAPI 3.0 spec at `/docs`
- [x] 13.14 Implement school signup endpoint (public, creates tenant + admin user + provisions subdomain)
- [x] 13.15 Implement server entry point with graceful shutdown

## 14. Integration & Validation

- [x] 14.1 Run `openspec validate school-erp-v1-foundation --type change --strict` to verify all artifacts
- [x] 14.2 Verify all spec scenarios are covered by tasks
- [x] 14.3 Verify ADRs are consistent with design decisions
- [ ] 14.4 Run TypeScript type-check across all packages
- [ ] 14.5 Run linting across all packages
