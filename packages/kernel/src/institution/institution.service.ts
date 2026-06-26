import { PrismaClient, Institution, InstitutionStatus, InstitutionType } from '@school-erp/database';

export interface CreateInstitutionInput {
  tenantId: string;
  name: string;
  type?: InstitutionType;
  address?: string;
  phone?: string;
  email?: string;
  website?: string;
}

export interface UpdateInstitutionInput {
  name?: string;
  type?: InstitutionType;
  address?: string;
  phone?: string;
  email?: string;
  website?: string;
  logo?: string;
}

export interface ListInstitutionsOptions {
  tenantId: string;
  status?: InstitutionStatus;
  type?: InstitutionType;
  limit?: number;
  offset?: number;
}

export class InstitutionService {
  constructor(private prisma: PrismaClient) {}

  // Create a new institution
  async create(data: CreateInstitutionInput): Promise<Institution> {
    // Verify tenant exists
    const tenant = await this.prisma.tenant.findUnique({
      where: { id: data.tenantId }
    });

    if (!tenant) {
      throw new Error(`Tenant with ID "${data.tenantId}" not found`);
    }

    if (tenant.status !== 'ACTIVE') {
      throw new Error(`Cannot create institution for inactive tenant`);
    }

    return this.prisma.institution.create({
      data: {
        tenantId: data.tenantId,
        name: data.name,
        type: data.type || 'SCHOOL',
        status: 'ONBOARDING',
        address: data.address,
        phone: data.phone,
        email: data.email,
        website: data.website
      }
    });
  }

  // Get institution by ID (excludes soft-deleted)
  async getById(id: string): Promise<Institution | null> {
    return this.prisma.institution.findFirst({
      where: { id, deletedAt: null }
    });
  }

  // List institutions for a tenant (excludes soft-deleted)
  async list(options: ListInstitutionsOptions): Promise<Institution[]> {
    const { tenantId, status, type, limit = 10, offset = 0 } = options;

    return this.prisma.institution.findMany({
      where: {
        tenantId,
        deletedAt: null,
        ...(status && { status }),
        ...(type && { type })
      },
      take: limit,
      skip: offset,
      orderBy: { createdAt: 'desc' }
    });
  }

  // Update institution
  async update(id: string, data: UpdateInstitutionInput): Promise<Institution> {
    const existing = await this.prisma.institution.findUnique({
      where: { id }
    });

    if (!existing) {
      throw new Error(`Institution with ID "${id}" not found`);
    }

    return this.prisma.institution.update({
      where: { id },
      data
    });
  }

  // Complete onboarding - transition to active
  async completeOnboarding(id: string): Promise<Institution> {
    const existing = await this.prisma.institution.findUnique({
      where: { id }
    });

    if (!existing) {
      throw new Error(`Institution with ID "${id}" not found`);
    }

    if (existing.status !== 'ONBOARDING') {
      throw new Error(`Can only complete onboarding for institutions in ONBOARDING status`);
    }

    return this.prisma.institution.update({
      where: { id },
      data: { status: 'ACTIVE' }
    });
  }

  // Suspend institution
  async suspend(id: string): Promise<Institution> {
    const existing = await this.prisma.institution.findUnique({
      where: { id }
    });

    if (!existing) {
      throw new Error(`Institution with ID "${id}" not found`);
    }

    if (existing.status === 'SUSPENDED') {
      throw new Error(`Institution is already suspended`);
    }

    if (existing.status === 'ARCHIVED') {
      throw new Error(`Cannot suspend archived institution`);
    }

    return this.prisma.institution.update({
      where: { id },
      data: { status: 'SUSPENDED' }
    });
  }

  // Reactivate institution
  async reactivate(id: string): Promise<Institution> {
    const existing = await this.prisma.institution.findUnique({
      where: { id }
    });

    if (!existing) {
      throw new Error(`Institution with ID "${id}" not found`);
    }

    if (existing.status !== 'SUSPENDED') {
      throw new Error(`Can only reactivate suspended institutions`);
    }

    return this.prisma.institution.update({
      where: { id },
      data: { status: 'ACTIVE' }
    });
  }

  // Archive institution (soft delete)
  async archive(id: string): Promise<Institution> {
    const existing = await this.prisma.institution.findUnique({
      where: { id }
    });

    if (!existing) {
      throw new Error(`Institution with ID "${id}" not found`);
    }

    if (existing.status === 'ARCHIVED') {
      throw new Error(`Institution is already archived`);
    }

    return this.prisma.institution.update({
      where: { id },
      data: {
        status: 'ARCHIVED',
        deletedAt: new Date()
      }
    });
  }

  // Get institution with stats (excludes soft-deleted)
  async getStats(id: string) {
    const institution = await this.prisma.institution.findFirst({
      where: { id, deletedAt: null },
      include: {
        users: { where: { deletedAt: null } },
        orgUnits: { where: { deletedAt: null } }
      }
    });

    if (!institution) {
      throw new Error(`Institution with ID "${id}" not found`);
    }

    return {
      id: institution.id,
      name: institution.name,
      type: institution.type,
      status: institution.status,
      userCount: institution.users.length,
      orgUnitCount: institution.orgUnits.length,
      createdAt: institution.createdAt,
      updatedAt: institution.updatedAt
    };
  }

  // Get active institutions for a tenant (excludes soft-deleted)
  async getActiveByTenant(tenantId: string): Promise<Institution[]> {
    return this.prisma.institution.findMany({
      where: {
        tenantId,
        status: 'ACTIVE',
        deletedAt: null
      },
      orderBy: { name: 'asc' }
    });
  }
}
