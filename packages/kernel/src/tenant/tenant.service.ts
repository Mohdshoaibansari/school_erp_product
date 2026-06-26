import { PrismaClient, Tenant, TenantStatus } from '@school-erp/database';

export interface CreateTenantInput {
  name: string;
  slug: string;
}

export interface UpdateTenantInput {
  name?: string;
  slug?: string;
}

export interface ListTenantsOptions {
  status?: TenantStatus;
  limit?: number;
  offset?: number;
}

export class TenantService {
  constructor(private prisma: PrismaClient) {}

  // Create a new tenant with first institution
  async create(data: CreateTenantInput): Promise<Tenant> {
    // Check if slug is already taken
    const existing = await this.prisma.tenant.findUnique({
      where: { slug: data.slug }
    });

    if (existing) {
      throw new Error(`Tenant with slug "${data.slug}" already exists`);
    }

    // Create tenant with first institution
    return this.prisma.tenant.create({
      data: {
        name: data.name,
        slug: data.slug,
        status: 'ACTIVE',
        institutions: {
          create: {
            name: `${data.name} - Main Campus`,
            type: 'SCHOOL',
            status: 'ONBOARDING'
          }
        }
      },
      include: {
        institutions: true
      }
    });
  }

  // Get tenant by ID (excludes soft-deleted)
  async getById(id: string): Promise<Tenant | null> {
    return this.prisma.tenant.findFirst({
      where: { id, deletedAt: null }
    });
  }

  // Get tenant by slug (excludes soft-deleted)
  async getBySlug(slug: string): Promise<Tenant | null> {
    return this.prisma.tenant.findFirst({
      where: { slug, deletedAt: null }
    });
  }

  // List tenants with optional filters (excludes soft-deleted)
  async list(options: ListTenantsOptions = {}): Promise<Tenant[]> {
    const { status, limit = 10, offset = 0 } = options;

    return this.prisma.tenant.findMany({
      where: {
        deletedAt: null,
        ...(status ? { status } : {})
      },
      take: limit,
      skip: offset,
      orderBy: { createdAt: 'desc' }
    });
  }

  // Update tenant
  async update(id: string, data: UpdateTenantInput): Promise<Tenant> {
    // Check if tenant exists
    const existing = await this.prisma.tenant.findUnique({
      where: { id }
    });

    if (!existing) {
      throw new Error(`Tenant with ID "${id}" not found`);
    }

    // If slug is being changed, check uniqueness
    if (data.slug && data.slug !== existing.slug) {
      const slugTaken = await this.prisma.tenant.findUnique({
        where: { slug: data.slug }
      });

      if (slugTaken) {
        throw new Error(`Tenant with slug "${data.slug}" already exists`);
      }
    }

    return this.prisma.tenant.update({
      where: { id },
      data
    });
  }

  // Suspend tenant and all institutions
  async suspend(id: string): Promise<Tenant> {
    const existing = await this.prisma.tenant.findUnique({
      where: { id },
      include: { institutions: true }
    });

    if (!existing) {
      throw new Error(`Tenant with ID "${id}" not found`);
    }

    if (existing.status === 'SUSPENDED') {
      throw new Error(`Tenant is already suspended`);
    }

    // Suspend tenant and all institutions
    return this.prisma.tenant.update({
      where: { id },
      data: {
        status: 'SUSPENDED',
        institutions: {
          updateMany: {
            where: { status: { not: 'ARCHIVED' } },
            data: { status: 'SUSPENDED' }
          }
        }
      }
    });
  }

  // Reactivate tenant
  async reactivate(id: string): Promise<Tenant> {
    const existing = await this.prisma.tenant.findUnique({
      where: { id }
    });

    if (!existing) {
      throw new Error(`Tenant with ID "${id}" not found`);
    }

    if (existing.status !== 'SUSPENDED') {
      throw new Error(`Can only reactivate suspended tenants`);
    }

    return this.prisma.tenant.update({
      where: { id },
      data: { status: 'ACTIVE' }
    });
  }

  // Archive tenant (soft delete)
  async archive(id: string): Promise<Tenant> {
    const existing = await this.prisma.tenant.findUnique({
      where: { id }
    });

    if (!existing) {
      throw new Error(`Tenant with ID "${id}" not found`);
    }

    return this.prisma.tenant.update({
      where: { id },
      data: {
        status: 'ARCHIVED',
        deletedAt: new Date()
      }
    });
  }

  // Get tenant statistics (excludes soft-deleted)
  async getStats(id: string) {
    const tenant = await this.prisma.tenant.findFirst({
      where: { id, deletedAt: null },
      include: {
        institutions: { where: { deletedAt: null } },
        users: { where: { deletedAt: null } }
      }
    });

    if (!tenant) {
      throw new Error(`Tenant with ID "${id}" not found`);
    }

    return {
      id: tenant.id,
      name: tenant.name,
      status: tenant.status,
      institutionCount: tenant.institutions.length,
      userCount: tenant.users.length,
      createdAt: tenant.createdAt,
      updatedAt: tenant.updatedAt
    };
  }
}
