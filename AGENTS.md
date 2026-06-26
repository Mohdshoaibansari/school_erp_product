# AGENTS.md

## OpenSpec Workflow

- For OpenSpec propose/apply/verify/archive workflows, use the local `openspec-git-discipline` skill to enforce proposal commits before apply and merge-before-archive discipline.

## Branch Discipline

- **Implementation must happen on `main` branch only.**
- Before running `/opsx-apply`, check current branch with `git branch --show-current`.
- If not on `main`, **stop and remind the user** to switch to main first.
- Syncing specs to main (`/opsx-sync`) should happen **after** implementation confirms specs are correct, not before.
- One spec at a time: sync a single capability spec to main, implement it, verify, then move to the next.

---

## Coding Conventions

### Service Structure Pattern

Every service MUST follow this structure:

```typescript
import { PrismaClient } from '@school-erp/database';

// 1. Define input/output interfaces ABOVE the class
export interface CreateEntityInput {
  name: string;
  status?: EntityStatus;
}

export interface UpdateEntityInput {
  name?: string;
  status?: EntityStatus;
}

// 2. Service class with dependency injection
export class EntityService {
  constructor(private prisma: PrismaClient) {}

  // 3. Methods follow: validate → check → execute → return
  async create(input: CreateEntityInput): Promise<Entity> {
    // Validate input
    if (!input.name || input.name.trim().length === 0) {
      throw new Error('Entity name is required');
    }

    // Execute
    return this.prisma.entity.create({
      data: { name: input.name },
    });
  }
}
```
---

### ALWAYS validate before modifying data
```
async suspend(id: string): Promise<User> {
  // ✅ GOOD: Validate entity exists
  const user = await this.prisma.user.findUnique({ where: { id } });
  if (!user) {
    throw new Error('User not found');
  }

  // ✅ GOOD: Validate status transition is legal
  if (user.status !== 'ACTIVE') {
    throw new Error(`Cannot suspend user in ${user.status} status`);
  }

  // ✅ GOOD: Execute only after validation passes
  return this.prisma.user.update({
    where: { id },
    data: { status: 'SUSPENDED' },
  });
}

```

### ALWAYS filter soft-deleted records

```
// ✅ GOOD: Filter deletedAt
const user = await this.prisma.user.findFirst({
  where: {
    id,
    deletedAt: null,  // Exclude soft-deleted
  },
});

// ✅ GOOD: Soft delete sets deletedAt
async archive(id: string): Promise<User> {
  return this.prisma.user.update({
    where: { id },
    data: {
      status: 'ARCHIVED',
      deletedAt: new Date(),  // Mark as deleted
    },
  });
}
```
### Tenant Isolation

```
// ✅ GOOD: Always include tenantId in queries
const users = await this.prisma.user.findMany({
  where: {
    tenantId,  // Scope to tenant
    deletedAt: null,
  },
});

// ❌ BAD: Missing tenantId — data leak risk!
const users = await this.prisma.user.findMany({
  where: { deletedAt: null },
});
```

### Use descriptive, actionable error messages:

```
// ✅ GOOD: Specific, tells user what's wrong
throw new Error('Cannot suspend user in ARCHIVED status');
throw new Error('Student limit reached (100/100). Please upgrade your subscription.');
throw new Error('Password already set. Use change password instead.');

// ❌ BAD: Generic, unhelpful
throw new Error('Error');
throw new Error('Invalid input');
throw new Error('Something went wrong');
```

### Status Transition Validations

```
// User lifecycle: INVITED → ACTIVE → SUSPENDED → ARCHIVED
// Valid transitions:
//   INVITED  → ACTIVE (activate)
//   ACTIVE   → SUSPENDED (suspend)
//   SUSPENDED → ACTIVE (reactivate)
//   ACTIVE   → ARCHIVED (archive)
// Invalid transitions:
//   ARCHIVED → ACTIVE (cannot reactivate archived)
//   INVITED  → SUSPENDED (must activate first)

async activate(id: string): Promise<User> {
  const user = await this.getById(id);
  if (!user) throw new Error('User not found');
  if (user.status !== 'INVITED') {
    throw new Error(`Cannot activate user in ${user.status} status`);
  }
  // ... execute transition
}
```

### CRUD Service Template

```
export class EntityService {
  constructor(private prisma: PrismaClient) {}

  async create(input: CreateEntityInput): Promise<Entity> {
    return this.prisma.entity.create({ data: input });
  }

  async getById(id: string): Promise<Entity | null> {
    return this.prisma.entity.findUnique({
      where: { id, deletedAt: null },
    });
  }

  async list(options: ListEntityOptions = {}): Promise<Entity[]> {
    const { skip = 0, take = 50, where, orderBy } = options;
    return this.prisma.entity.findMany({
      skip,
      take,
      where: { ...where, deletedAt: null },
      orderBy: orderBy || { createdAt: 'desc' },
    });
  }

  async update(id: string, data: UpdateEntityInput): Promise<Entity> {
    const entity = await this.getById(id);
    if (!entity) throw new Error('Entity not found');
    return this.prisma.entity.update({ where: { id }, data });
  }

  async archive(id: string): Promise<Entity> {
    const entity = await this.getById(id);
    if (!entity) throw new Error('Entity not found');
    if (entity.status === 'ARCHIVED') {
      throw new Error('Entity is already archived');
    }
    return this.prisma.entity.update({
      where: { id },
      data: { status: 'ARCHIVED', deletedAt: new Date() },
    });
  }
}

```

### Paginated List Pattern
```
interface PaginatedResult<T> {
  data: T[];
  total: number;
  skip: number;
  take: number;
}

async listUsers(options: ListUsersOptions): Promise<PaginatedResult<User>> {
  const { skip = 0, take = 50, where } = options;
  
  const [data, total] = await Promise.all([
    this.prisma.user.findMany({
      skip,
      take,
      where: { ...where, deletedAt: null },
      orderBy: { createdAt: 'desc' },
    }),
    this.prisma.user.count({
      where: { ...where, deletedAt: null },
    }),
  ]);

  return { data, total, skip, take };
}
```

### Scoped Query Pattern

```
// Queries scoped to institution
async getStudents(institutionId: string): Promise<Student[]> {
  return this.prisma.student.findMany({
    where: {
      institutionId,
      deletedAt: null,
    },
  });
}
```

### Method Naming Conventions

| Pattern | Use When | Examples |
|---------|----------|----------|
| `create(data)` | Creating new records | `createUser`, `createRole` |
| `getById(id)` | Fetching single record by ID | `getById`, `getByEmail` |
| `list(options)` | Fetching multiple records | `listUsers`, `list({ skip, take })` |
| `update(id, data)` | Updating existing record | `updateUser`, `updateRole` |
| `delete(id)` | Soft or hard delete | `deleteUser`, `archiveUser` |
| `[verb](id)` | Lifecycle actions | `activate`, `suspend`, `archive`, `reactivate` |
| `check[Condition]` | Boolean checks | `checkStudentCap`, `checkPermission` |
| `get[Property]` | Get derived/computed values | `getAvailableModules`, `getTier` |

### Input/Output Interface Naming

| Pattern | Use When | Examples |
|---------|----------|----------|
| `Create[Entity]Input` | Create method input | `CreateUserInput`, `CreateRoleInput` |
| `Update[Entity]Input` | Update method input | `UpdateUserInput`, `UpdateProfileInput` |
| `[Entity]Info` | Entity data returned | `TierInfo`, `ModuleInfo` |
| `[Action]Result` | Operation result | `TokenPair`, `EntitlementCheckResult` |
| `List[Entity]Options` | List method options | `ListUsersOptions` |

### Required Validation Checklist

For EVERY service method that modifies data, check ALL that apply:

- [ ] **Entity exists** — `findUnique` returns null? → throw "not found"
- [ ] **Entity belongs to tenant** — `tenantId` mismatch? → throw "not found" (not "access denied" — don't leak existence)
- [ ] **Status transition valid** — Invalid state change? → throw "cannot [action] in [status] status"
- [ ] **Required relations exist** — Missing foreign key? → throw "[relation] not found"
- [ ] **Unique constraints** — Duplicate? → throw "[field] already exists"
- [ ] **Business rules** — Cap reached? Limit exceeded? → throw descriptive error

---

## File Organization

### Package Structure

```
packages/
├── database/           # Prisma schema + client
│   ├── prisma/
│   │   └── schema.prisma
│   └── src/
│       └── index.ts    # Re-exports + tenant middleware
├── kernel/             # Core services
│   └── src/
│       ├── tenant/
│       ├── identity/
│       ├── auth/
│       ├── authorization/
│       └── subscription/
├── shared/             # Types, validation, errors
└── modules/            # Business modules (attendance, students, fees)
```

### Service File Naming

- **Service**: `[name].service.ts` (e.g., `user.service.ts`, `auth.service.ts`)
- **Middleware**: `[name].middleware.ts` (e.g., `entitlement.middleware.ts`)
- **Config**: `[name].config.ts` (e.g., `tier-config.ts`)
- **Types**: `[name].types.ts` (if complex types need separate file)

### Export Pattern

Each service directory has `index.ts` that re-exports:

```typescript
// packages/kernel/src/identity/index.ts
export * from './user.service';
export * from './user-profile.service';
```

Package root re-exports all services:

```typescript
// packages/kernel/src/index.ts
export * from './tenant';
export * from './identity';
export * from './auth';
export * from './authorization';
export * from './subscription';
```

---

## Code Quality Checklist

Before marking a task complete, verify:

- [ ] All interfaces are properly typed (no `any`)
- [ ] All async methods return `Promise<T>`
- [ ] All error messages are descriptive and actionable
- [ ] All queries filter `deletedAt: null` for active records
- [ ] All queries include `tenantId` for tenant isolation
- [ ] All mutations validate entity exists before updating
- [ ] All status transitions are validated
- [ ] All unique constraints are checked before create
- [ ] Service is exported from package index

---

## Testing Expectations

When implementing a service:

1. **Unit tests**: Test each method in isolation
2. **Integration tests**: Test with real database (test DB)
3. **Edge cases**: Test error paths, not just happy paths
4. **Tenant isolation**: Verify cross-tenant access is blocked

---

## Anti-Patterns to Avoid

| ❌ Anti-Pattern | ✅ Correct Pattern |
|----------------|-------------------|
| Generic error messages | Specific, actionable errors |
| No validation before mutation | Validate → Check → Execute |
| Missing tenant isolation | Always include `tenantId` |
| Ignoring soft deletes | Always filter `deletedAt: null` |
| Direct Prisma calls in controllers | Use service classes |
| Business logic in controllers | Business logic in services |
| Hardcoded values | Use config service or constants |
| No input validation | Validate all inputs |
| Assuming entity exists | Check existence first |
| No status transition checks | Validate state machine |