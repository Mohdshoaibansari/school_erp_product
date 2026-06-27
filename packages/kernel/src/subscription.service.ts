import prisma from '@school-erp/database';
import { ModuleName, StudentLimitExceededError, ModuleNotEnabledError } from '@school-erp/shared';

const FREE_MODULES: ModuleName[] = ['students', 'attendance', 'fees'];

export class SubscriptionService {
  constructor(private db = prisma) {}

  async setupFreeTier(tenantId: string) {
    const modules = FREE_MODULES.map(moduleName => ({
      tenantId,
      moduleName,
      enabled: true,
      isPaid: false,
    }));

    for (const mod of modules) {
      await this.db.tenantModule.create({ data: mod });
    }
  }

  async isModuleEnabled(tenantId: string, moduleName: ModuleName): Promise<boolean> {
    const mod = await this.db.tenantModule.findUnique({
      where: { tenantId_moduleName: { tenantId, moduleName } },
    });
    return mod?.enabled ?? false;
  }

  async enforceModuleEnabled(tenantId: string, moduleName: ModuleName): Promise<void> {
    const enabled = await this.isModuleEnabled(tenantId, moduleName);
    if (!enabled) throw new ModuleNotEnabledError(moduleName);
  }

  async enableModule(tenantId: string, moduleName: ModuleName) {
    return this.db.tenantModule.upsert({
      where: { tenantId_moduleName: { tenantId, moduleName } },
      update: { enabled: true, isPaid: true },
      create: { tenantId, moduleName, enabled: true, isPaid: true },
    });
  }

  async disableModule(tenantId: string, moduleName: ModuleName) {
    return this.db.tenantModule.upsert({
      where: { tenantId_moduleName: { tenantId, moduleName } },
      update: { enabled: false },
      create: { tenantId, moduleName, enabled: false },
    });
  }

  async getEnabledModules(tenantId: string) {
    return this.db.tenantModule.findMany({
      where: { tenantId, enabled: true },
    });
  }

  async checkStudentLimit(tenantId: string): Promise<void> {
    const tenant = await this.db.tenant.findUnique({ where: { id: tenantId } });
    if (!tenant) return;

    const count = await this.db.student.count({
      where: { tenantId, status: 'ACTIVE', deletedAt: null },
    });

    if (count >= tenant.studentLimit) {
      throw new StudentLimitExceededError(tenant.studentLimit);
    }
  }

  async getStudentLimitStatus(tenantId: string) {
    const tenant = await this.db.tenant.findUnique({ where: { id: tenantId } });
    if (!tenant) return null;

    const count = await this.db.student.count({
      where: { tenantId, status: 'ACTIVE', deletedAt: null },
    });

    return {
      current: count,
      limit: tenant.studentLimit,
      isAtLimit: count >= tenant.studentLimit,
    };
  }
}
