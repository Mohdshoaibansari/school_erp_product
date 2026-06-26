import { PrismaClient, SubscriptionTier, ModuleEntitlement, Tenant } from '@school-erp/database';

export interface TierInfo {
  id: string;
  name: string;
  description: string | null;
  studentCap: number | null;
  modules: ModuleInfo[];
}

export interface ModuleInfo {
  code: string;
  enabled: boolean;
}

export interface CreateTierInput {
  name: string;
  description?: string;
  studentCap?: number;
  modules: { code: string; enabled: boolean }[];
}

export interface UpdateTierInput {
  name?: string;
  description?: string;
  studentCap?: number | null;
}

export interface StudentCapCheckResult {
  allowed: boolean;
  current: number;
  cap: number | null;
}

export class SubscriptionService {
  constructor(private prisma: PrismaClient) {}

  async getTier(tenantId: string): Promise<TierInfo | null> {
    const tenant = await this.prisma.tenant.findFirst({
      where: { id: tenantId, deletedAt: null },
      include: {
        tier: {
          include: {
            modules: true,
          },
        },
      },
    });

    if (!tenant || !tenant.tier) {
      return null;
    }

    return {
      id: tenant.tier.id,
      name: tenant.tier.name,
      description: tenant.tier.description,
      studentCap: tenant.tier.studentCap,
      modules: tenant.tier.modules.map((m) => ({
        code: m.moduleCode,
        enabled: m.enabled,
      })),
    };
  }

  async getAvailableModules(tenantId: string): Promise<string[]> {
    const tier = await this.getTier(tenantId);
    if (!tier) {
      return [];
    }

    return tier.modules
      .filter((m) => m.enabled)
      .map((m) => m.code);
  }

  async isModuleAvailable(tenantId: string, moduleCode: string): Promise<boolean> {
    const modules = await this.getAvailableModules(tenantId);
    return modules.includes(moduleCode);
  }

  async checkStudentCap(tenantId: string): Promise<StudentCapCheckResult> {
    const tier = await this.getTier(tenantId);
    
    // If no tier or no student cap, unlimited
    if (!tier || tier.studentCap === null) {
      return {
        allowed: true,
        current: 0,
        cap: null,
      };
    }

    // Count active students for this tenant
    // Uses UserInstitution as a proxy for student count
    const current = await this.prisma.userInstitution.count({
      where: {
        institution: { tenantId, deletedAt: null },
        user: { deletedAt: null },
      },
    });

    return {
      allowed: current < tier.studentCap,
      current,
      cap: tier.studentCap,
    };
  }

  async setTenantTier(tenantId: string, tierId: string): Promise<void> {
    const tier = await this.prisma.subscriptionTier.findUnique({
      where: { id: tierId },
    });

    if (!tier) {
      throw new Error('Subscription tier not found');
    }

    await this.prisma.tenant.update({
      where: { id: tenantId },
      data: { tierId },
    });
  }

  async getTiers(): Promise<SubscriptionTier[]> {
    return this.prisma.subscriptionTier.findMany({
      include: {
        modules: true,
      },
    });
  }

  async createTier(data: CreateTierInput): Promise<SubscriptionTier> {
    return this.prisma.subscriptionTier.create({
      data: {
        name: data.name,
        description: data.description,
        studentCap: data.studentCap,
        modules: {
          create: data.modules.map((m) => ({
            moduleCode: m.code,
            enabled: m.enabled,
          })),
        },
      },
      include: {
        modules: true,
      },
    });
  }

  async updateTier(
    tierId: string,
    data: UpdateTierInput
  ): Promise<SubscriptionTier> {
    return this.prisma.subscriptionTier.update({
      where: { id: tierId },
      data,
      include: {
        modules: true,
      },
    });
  }

  async setModuleEntitlement(
    tierId: string,
    moduleCode: string,
    enabled: boolean
  ): Promise<ModuleEntitlement> {
    return this.prisma.moduleEntitlement.upsert({
      where: {
        tierId_moduleCode: {
          tierId,
          moduleCode,
        },
      },
      update: { enabled },
      create: {
        tierId,
        moduleCode,
        enabled,
      },
    });
  }
}
