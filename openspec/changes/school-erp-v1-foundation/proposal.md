## Why

Indian schools lack affordable, multi-tenant ERP systems that adapt to their diverse academic structures (CBSE, State Board, ICSE) without forcing a one-size-fits-all hierarchy. Schools need a system that works from day one for core operations — student records, attendance, fees, timetable, and exams — while allowing per-school customization of academic levels, sections, and naming conventions. Building a shared SaaS backend with Supabase enables rapid iteration, built-in auth, and PostgreSQL-level data isolation, while the monorepo structure allows separate frontend/mobile apps to consume well-documented REST APIs.

## What Changes

- **New monorepo scaffold** using pnpm workspaces with packages for database, shared utilities, kernel services, five business modules (students, attendance, fees, timetable, exams), and a Fastify API server with auto-generated OpenAPI documentation.
- **Multi-tenant foundation** with subdomain routing (`school.schoolerp.com`), shared database with tenant-scoped data, and optional dedicated-deployment support.
- **Supabase Auth integration** for email magic-link authentication, user identity management, and session handling.
- **Configurable academic structure** allowing each school to define its own hierarchy of levels (Class, Section, Stream) with custom naming and ordering.
- **Role-based access control** with attribute-based data scoping — teachers see only their assigned classes for attendance and their assigned subjects for homework/grades.
- **Five business modules** delivered as separate packages: Student Management (free), Attendance (free), Fee Management (free), Timetable (paid add-on), Exams & Grades (paid add-on).
- **Subscription and module gating** with a free tier (100-student hard cap, three core modules) and paid à la carte modules selectable by the school admin.
- **Self-service school onboarding** with signup form, subdomain provisioning, magic-link verification, and a guided setup wizard for first-time admins.
- **Academic year lifecycle** supporting bulk student promotion per class with historical data preservation across years.
- **Bulk student import** via CSV spreadsheet plus manual single-entry for mid-year additions.

## Capabilities

### New Capabilities

- `tenant-institution`: Self-service school signup, subdomain provisioning, tenant isolation, onboarding wizard, and dedicated-deployment option.
- `authentication`: Supabase Auth integration with subdomain-aware magic-link login, session management, and user verification.
- `identity-users`: User profile management, role assignment (Super Admin, School Admin, Principal, Teacher, Accountant), and staff invitation.
- `authorization`: RBAC permissions plus attribute-based data scoping — class teacher sees only assigned section for attendance, subject teacher sees only assigned classes for grades/homework. Many-to-many teacher-class relationships.
- `academic-structure`: Configurable academic hierarchy per school (Class, Section, Stream levels with custom naming), subject catalog, and academic year/term management.
- `subscription-management`: Module enablement per school, free tier with 100-student hard cap, paid à la carte module add-ons, and student limit enforcement.
- `student-management`: Student enrollment with bulk CSV import and manual entry, student profiles with guardian information, class assignment, and academic year promotion.
- `attendance`: Daily attendance marking per section with attribute-scoped views, bulk marking, and attendance reports. Teacher sees only their assigned sections.
- `fee-management`: Fee structure definition per class, fee collection recording, receipt generation, and pending dues reporting.
- `timetable`: Weekly class schedule grid with subject, teacher, and room allocation per section. Paid add-on module.
- `exams-grades`: Exam schedule management, marks entry per subject/student, and report card generation. Paid add-on module.

### Modified Capabilities

None — this is a greenfield project with no existing capabilities to modify.

## Impact

- **New repository structure**: Full monorepo scaffold with `packages/database`, `packages/shared`, `packages/kernel`, five module packages, and `apps/api`.
- **Database**: Prisma schema with tenant-scoped tables for all modules, Supabase-managed `auth.users`, and Row Level Security policies for tenant isolation.
- **API server**: Fastify with `@fastify/swagger` for auto-generated OpenAPI 3.0 documentation at `/docs`.
- **Frontend integration**: REST API consumed by separate web and mobile applications (not in this change scope).
- **Dependencies**: Supabase (Auth, Postgres, RLS), Prisma ORM, Fastify, pnpm workspaces.
- **No breaking changes**: Greenfield build with no existing code affected.
