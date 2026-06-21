## Why

The School ERP platform needs a lean, buildable foundation. The previous design listed 25 platform capabilities — many of which are thin data models that don't warrant their own service abstraction. This change defines the true kernel (services with real logic) and simplifies the rest into tables consumed directly by business modules. This keeps the platform simple to build while retaining the extensibility needed for future elaboration.

## What Changes

- Define kernel services: Tenant (C-01), Users (C-02), Auth (C-03), AuthZ (C-04), Academic (C-05), Subscription (C-07), Config+Rules Engine (C-08), Calendar, Audit (C-11)
- Simplify to data tables: Relationships (C-06), Code Gen (C-12), Addresses (C-13), Documents (C-14) — no service wrapper, modules join directly
- Simplify Notifications (C-09) and Communication (C-10) to basic email delivery with simple message tables — elaborate later as cross-cutting services
- Defer entirely: Workflow (C-15), Groups (C-17), Bulk Ops (C-18), Export (C-19), Tasks (C-20), Search (C-21), Analytics (C-22), Billing (C-23), Integration (C-24)

## Capabilities

### New Capabilities

- `tenant-institution`: Multi-tenant root with institutions, org units, lifecycle management
- `identity-users`: Unified user model with profiles, categories, and institution-scoped role assignments
- `authentication`: Centralized login with email/password, JWT, OTP, rate limiting
- `authorization`: RBAC with institution-scoped roles, permission checks, scope resolution
- `academic-structure`: Configurable academic model — years, terms, grades, classes, sections, subjects
- `subscription-management`: Tier tracking, student cap enforcement, entitlement checks
- `config-rules-engine`: Typed configuration with scope inheritance plus evaluatable rule definitions for attendance, fees, leave, etc.
- `calendar-service`: School day definitions, holidays, exam schedules, event tracking for attendance calculation
- `audit-logging`: Append-only audit trail with configurable retention per level
- `simple-notifications`: Email delivery through template-based notification sending
- `simple-communication`: Direct teacher-parent messaging with conversation threads
- `simple-relationships`: Student-guardian mapping table with type and contact role
- `simple-code-generation`: Auto-incrementing identifier sequences per scope
- `simple-addresses`: Structured address records linked to entities
- `simple-documents`: File upload and download with storage abstraction

### Modified Capabilities

(none — first set of specs)

## Impact

- Reduces platform scope from 25 capabilities to ~15 implementable units
- Simplifies the architecture: services where logic lives, tables where data lives
- Modules consume relationships, addresses, documents, and identifiers via direct SQL joins — no service dependency
- Notifications and Communication are intentionally thin; can be refactored into proper services later
- All deferred capabilities (Workflow, Groups, etc.) can be added as needed without breaking existing code
