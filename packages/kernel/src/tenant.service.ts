import prisma from '@school-erp/database';
import { NotFoundError, TenantStatus, ModuleName } from '@school-erp/shared';

export interface CreateTenantInput {
  name: string;
  subdomain: string;
  adminEmail: string;
  adminName: string;
  adminPhone?: string;
}

export class TenantService {
  constructor(private db = prisma) {}

  async create(input: CreateTenantInput) {
    const tenant = await this.db.tenant.create({
      data: {
        name: input.name,
        subdomain: input.subdomain,
        studentLimit: 100,
      },
    });
    return tenant;
  }

  async getById(id: string) {
    const tenant = await this.db.tenant.findUnique({ where: { id } });
    if (!tenant) throw new NotFoundError('Tenant not found');
    return tenant;
  }

  async getBySubdomain(subdomain: string) {
    const tenant = await this.db.tenant.findUnique({ where: { subdomain } });
    if (!tenant) throw new NotFoundError('Tenant not found');
    return tenant;
  }

  async updateStatus(id: string, status: TenantStatus) {
    const tenant = await this.db.tenant.update({
      where: { id },
      data: { status },
    });
    return tenant;
  }

  async updateStudentLimit(id: string, limit: number) {
    return this.db.tenant.update({
      where: { id },
      data: { studentLimit: limit },
    });
  }

  async getStudentCount(tenantId: string) {
    return this.db.student.count({
      where: { tenantId, status: 'ACTIVE', deletedAt: null },
    });
  }
}
