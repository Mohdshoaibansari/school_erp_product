import { PrismaClient } from '@prisma/client';
import { AsyncLocalStorage } from 'async_hooks';

export * from '@prisma/client';

// Thread-safe tenant context using AsyncLocalStorage
export interface TenantContext {
  tenantId: string;
}

const tenantStorage = new AsyncLocalStorage<TenantContext>();

export function setTenantContext(tenantId: string): void {
  tenantStorage.enterWith({ tenantId });
}

export function getTenantContext(): TenantContext | undefined {
  return tenantStorage.getStore();
}

export function getTenantId(): string | undefined {
  return tenantStorage.getStore()?.tenantId;
}

export function clearTenantContext(): void {
  tenantStorage.enterWith(undefined as any);
}

// Run a function with a specific tenant context
export function runWithTenant<T>(tenantId: string, fn: () => T): T {
  return tenantStorage.run({ tenantId }, fn);
}

// Models that don't require tenant filtering
const SKIP_TENANT_FILTER_MODELS = ['Tenant', 'OrgUnit', 'Permission'];

// Models that have tenantId field
const TENANT_MODELS = [
  'Institution',
  'User',
  'UserInstitution',
  'UserProfile',
  'Role',
  'RoleAssignment',
  'ModuleEntitlement',
];

// Create Prisma client with tenant middleware
export function createPrismaClient(): PrismaClient {
  const prisma = new PrismaClient();

  // Middleware to auto-filter by tenant_id on all queries
  prisma.$use(async (params, next) => {
    const tenantId = getTenantId();

    // Skip tenant filtering for models that don't need it
    if (SKIP_TENANT_FILTER_MODELS.includes(params.model)) {
      return next(params);
    }

    // Only apply tenant filtering to models that have tenantId
    if (!TENANT_MODELS.includes(params.model)) {
      return next(params);
    }

    // Validate tenant context exists for protected operations
    const protectedActions = ['create', 'update', 'upsert', 'delete'];
    if (protectedActions.includes(params.action) && !tenantId) {
      throw new Error('Tenant context required for write operations');
    }

    // Apply tenant_id filter to queries
    if (tenantId) {
      switch (params.action) {
        case 'findMany':
        case 'findFirst':
          params.args.where = {
            ...params.args.where,
            tenantId,
          };
          break;

        case 'findUnique':
          // Convert findUnique to findFirst with tenant filter
          params.action = 'findFirst';
          params.args.where = {
            ...params.args.where,
            tenantId,
          };
          break;

        case 'create':
          // Auto-add tenantId to create data
          params.args.data = {
            ...params.args.data,
            tenantId,
          };
          break;

        case 'update':
        case 'upsert':
          // Ensure updates are scoped to tenant
          params.args.where = {
            ...params.args.where,
            tenantId,
          };
          break;

        case 'delete':
          // Ensure deletes are scoped to tenant
          params.args.where = {
            ...params.args.where,
            tenantId,
          };
          break;

        case 'count':
          // Apply tenant filter to count queries
          params.args.where = {
            ...params.args.where,
            tenantId,
          };
          break;

        case 'aggregate':
          // Apply tenant filter to aggregate queries
          params.args.where = {
            ...params.args.where,
            tenantId,
          };
          break;
      }
    }

    return next(params);
  });

  return prisma;
}

// Singleton instance
let prismaInstance: PrismaClient | null = null;

export function getPrismaClient(): PrismaClient {
  if (!prismaInstance) {
    prismaInstance = createPrismaClient();
  }
  return prismaInstance;
}
