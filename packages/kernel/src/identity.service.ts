import prisma from '@school-erp/database';
import { NotFoundError, UserRole, UserStatus } from '@school-erp/shared';

export interface CreateUserInput {
  tenantId: string;
  email: string;
  name: string;
  phone?: string;
  role: UserRole;
  supabaseId: string;
}

export class IdentityService {
  constructor(private db = prisma) {}

  async createUser(input: CreateUserInput) {
    const existing = await this.db.userTenant.findUnique({
      where: { userId_tenantId: { userId: input.supabaseId, tenantId: input.tenantId } },
    });
    if (existing) throw new Error('User already exists in this school');

    let user = await this.db.user.findUnique({ where: { supabaseId: input.supabaseId } });
    if (!user) {
      user = await this.db.user.create({
        data: {
          supabaseId: input.supabaseId,
          email: input.email,
          name: input.name,
          phone: input.phone,
          status: 'ACTIVE',
        },
      });
    }

    await this.db.userTenant.create({
      data: {
        userId: user.id,
        tenantId: input.tenantId,
        role: input.role,
      },
    });

    return { user, role: input.role };
  }

  async getById(userId: string) {
    const user = await this.db.user.findUnique({
      where: { id: userId, deletedAt: null },
    });
    if (!user) throw new NotFoundError('User not found');
    return user;
  }

  async getBySupabaseId(supabaseId: string) {
    const user = await this.db.user.findUnique({
      where: { supabaseId, deletedAt: null },
    });
    if (!user) throw new NotFoundError('User not found');
    return user;
  }

  async getUserTenant(userId: string, tenantId: string) {
    const membership = await this.db.userTenant.findUnique({
      where: { userId_tenantId: { userId, tenantId } },
    });
    if (!membership) throw new NotFoundError('User is not a member of this school');
    return membership;
  }

  async getUsersByTenant(tenantId: string, skip = 0, take = 50) {
    const memberships = await this.db.userTenant.findMany({
      where: { tenantId },
      include: { user: true },
      skip,
      take,
    });
    return memberships;
  }

  async updateStatus(userId: string, status: UserStatus) {
    return this.db.user.update({
      where: { id: userId },
      data: { status, deletedAt: status === 'ARCHIVED' ? new Date() : undefined },
    });
  }

  async suspendUser(userId: string) {
    const user = await this.getById(userId);
    if (user.status === 'ARCHIVED') throw new Error('Cannot suspend archived user');
    return this.updateStatus(userId, 'SUSPENDED');
  }
}
