# Institution Service

**File:** `packages/kernel/src/institution/institution.service.ts`
**Exported from:** `packages/kernel/src/institution/index.ts`
**Package:** `@school-erp/kernel`

## Overview

The Institution service manages school/college/university records within a tenant. Each tenant can have multiple institutions, and each institution follows its own lifecycle from onboarding through activation, suspension, and archival.

Institutions are the operational unit for most business features — they own academic years, org units, subjects, calendar events, and role assignments.

## Data Model

The `Institution` model in Prisma schema (`packages/database/prisma/schema.prisma`):

| Field | Type | Notes |
|-------|------|-------|
| `id` | String (UUID) | Primary key |
| `tenantId` | String (FK) | References Tenant |
| `name` | String | Display name |
| `type` | InstitutionType enum | SCHOOL, COLLEGE, UNIVERSITY |
| `status` | InstitutionStatus enum | ONBOARDING, ACTIVE, SUSPENDED, ARCHIVED |
| `address` | String? | Physical address |
| `phone` | String? | Contact number |
| `email` | String? | Contact email |
| `website` | String? | URL |
| `logo` | String? | Logo image path/URL |
| `deletedAt` | DateTime? | Soft-delete timestamp |

### Relations
- `tenant: Tenant` — owning tenant
- `users: UserInstitution[]` — user-institution assignments
- `orgUnits: OrgUnit[]` — organizational hierarchy
- `roleAssignments: RoleAssignment[]` — scoped role assignments
- `academicYears: AcademicYear[]` — academic calendar
- `calendarEvents: CalendarEvent[]` — scheduled events
- `Subject: Subject[]` — subjects offered

### Status Lifecycle

```
ONBOARDING → ACTIVE → SUSPENDED → ARCHIVED
                 ↑         │
                 └─────────┘ (reactivate)
```

**Valid transitions:**

| From | To | Method | Conditions |
|------|----|--------|------------|
| ONBOARDING | ACTIVE | `completeOnboarding` | Institution must be in ONBOARDING |
| ACTIVE | SUSPENDED | `suspend` | Must not be already SUSPENDED or ARCHIVED |
| SUSPENDED | ACTIVE | `reactivate` | Must be in SUSPENDED |
| ACTIVE | ARCHIVED | `archive` | Must not be already ARCHIVED |
| SUSPENDED | ARCHIVED | `archive` | Must not be already ARCHIVED |

**Invalid transitions:**
- ARCHIVED → any state (terminal)
- ONBOARDING → SUSPENDED (must activate first)
- ONBOARDING → ARCHIVED (must activate first)

## Service Methods

### `create(data: CreateInstitutionInput): Promise<Institution>`

Creates a new institution under a tenant. New institutions start in ONBOARDING status.

```typescript
interface CreateInstitutionInput {
  tenantId: string;
  name: string;
  type?: InstitutionType;     // defaults to SCHOOL
  address?: string;
  phone?: string;
  email?: string;
  website?: string;
}
```

**Validation:**
- Tenant must exist and have ACTIVE status
- Throws descriptive error if tenant is missing or inactive

### `getById(id: string): Promise<Institution | null>`

Fetches by UUID. Excludes soft-deleted records.

### `list(options: ListInstitutionsOptions): Promise<Institution[]>`

Lists institutions for a tenant with optional status/type filtering and pagination.

```typescript
interface ListInstitutionsOptions {
  tenantId: string;
  status?: InstitutionStatus;
  type?: InstitutionType;
  limit?: number;   // default 10
  offset?: number;  // default 0
}
```

Always excludes soft-deleted records. Ordered by `createdAt` descending.

### `update(id: string, data: UpdateInstitutionInput): Promise<Institution>`

Updates editable fields. Checks existence before update — throws not found if missing.

### `completeOnboarding(id: string): Promise<Institution>`

Transitions institution from ONBOARDING to ACTIVE.

**Validation:**
- Institution must exist
- Must be in ONBOARDING status

### `suspend(id: string): Promise<Institution>`

Temporarily disables an institution.

**Validation:**
- Institution must exist
- Must not be already SUSPENDED
- Must not be ARCHIVED

### `reactivate(id: string): Promise<Institution>`

Reactivates a suspended institution back to ACTIVE.

**Validation:**
- Institution must exist
- Must be in SUSPENDED status

### `archive(id: string): Promise<Institution>`

Soft-deletes an institution. Sets status to ARCHIVED and `deletedAt` to current timestamp.

**Validation:**
- Institution must exist
- Must not be already ARCHIVED

### `getStats(id: string): Promise<InstitutionStats>`

Returns aggregated counts:

```typescript
{
  id: string;
  name: string;
  type: InstitutionType;
  status: InstitutionStatus;
  userCount: number;      // non-deleted user assignments
  orgUnitCount: number;   // non-deleted org units
  createdAt: DateTime;
  updatedAt: DateTime;
}
```

### `getActiveByTenant(tenantId: string): Promise<Institution[]>`

Returns all ACTIVE institutions for a tenant, ordered by name ascending. Used for listing operational schools in dashboards and enrollment flows.

## Patterns & Conventions

- All queries filter `deletedAt: null` for active records
- The service validates existence before every mutation
- Status transitions are validated with descriptive error messages
- Institution is tenant-scoped via `tenantId` — multi-tenant queries rely on the Prisma middleware for auto-filtering
