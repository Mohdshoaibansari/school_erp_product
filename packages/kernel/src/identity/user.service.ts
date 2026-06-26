import { PrismaClient, User, UserStatus, Prisma } from '@school-erp/database';

export interface CreateUserInput {
  email: string;
  passwordHash?: string;
  profile?: {
    firstName: string;
    lastName: string;
    phone?: string;
  };
}

export interface UpdateUserInput {
  email?: string;
  status?: UserStatus;
}

export interface ListUsersOptions {
  skip?: number;
  take?: number;
  where?: Prisma.UserWhereInput;
  orderBy?: Prisma.UserOrderByWithRelationInput;
}

export class UserService {
  constructor(private prisma: PrismaClient) {}

  async create(tenantId: string, data: CreateUserInput): Promise<User> {
    // Validate input
    if (!data.email || data.email.trim().length === 0) {
      throw new Error('Email is required');
    }

    // Check email uniqueness within tenant
    const existing = await this.prisma.user.findFirst({
      where: {
        tenantId,
        email: data.email,
        deletedAt: null,
      },
    });

    if (existing) {
      throw new Error(`User with email "${data.email}" already exists`);
    }

    return this.prisma.user.create({
      data: {
        tenantId,
        email: data.email,
        passwordHash: data.passwordHash,
        profile: data.profile
          ? {
              create: {
                firstName: data.profile.firstName,
                lastName: data.profile.lastName,
                phone: data.profile.phone,
              },
            }
          : undefined,
      },
      include: {
        profile: true,
      },
    });
  }

  async getById(id: string): Promise<User | null> {
    return this.prisma.user.findFirst({
      where: { id, deletedAt: null },
      include: {
        profile: true,
        institutions: {
          where: { institution: { deletedAt: null } },
          include: {
            institution: true,
          },
        },
      },
    });
  }

  async getByEmail(email: string): Promise<User | null> {
    return this.prisma.user.findFirst({
      where: { email, deletedAt: null },
      include: {
        profile: true,
      },
    });
  }

  async list(options: ListUsersOptions = {}): Promise<User[]> {
    const { skip = 0, take = 50, where, orderBy } = options;

    return this.prisma.user.findMany({
      skip,
      take,
      where: {
        ...where,
        deletedAt: null,
      },
      orderBy: orderBy || { createdAt: 'desc' },
      include: {
        profile: true,
      },
    });
  }

  async update(id: string, data: UpdateUserInput): Promise<User> {
    // Validate entity exists
    const existing = await this.prisma.user.findFirst({
      where: { id, deletedAt: null },
    });

    if (!existing) {
      throw new Error('User not found');
    }

    // If email is being changed, check uniqueness
    if (data.email && data.email !== existing.email) {
      const emailTaken = await this.prisma.user.findFirst({
        where: {
          tenantId: existing.tenantId,
          email: data.email,
          deletedAt: null,
          id: { not: id },
        },
      });

      if (emailTaken) {
        throw new Error(`User with email "${data.email}" already exists`);
      }
    }

    return this.prisma.user.update({
      where: { id },
      data,
      include: {
        profile: true,
      },
    });
  }

  async assignToInstitution(
    userId: string,
    institutionId: string,
    roleId: string
  ): Promise<void> {
    // Validate user exists
    const user = await this.prisma.user.findFirst({
      where: { id: userId, deletedAt: null },
    });
    if (!user) throw new Error('User not found');

    // Validate institution exists
    const institution = await this.prisma.institution.findFirst({
      where: { id: institutionId, deletedAt: null },
    });
    if (!institution) throw new Error('Institution not found');

    // Check for existing assignment
    const existing = await this.prisma.userInstitution.findFirst({
      where: { userId, institutionId },
    });
    if (existing) {
      throw new Error('User is already assigned to this institution');
    }

    await this.prisma.userInstitution.create({
      data: {
        userId,
        institutionId,
        roleId,
      },
    });
  }

  async removeFromInstitution(
    userId: string,
    institutionId: string
  ): Promise<void> {
    // Validate assignment exists
    const existing = await this.prisma.userInstitution.findFirst({
      where: { userId, institutionId },
    });
    if (!existing) {
      throw new Error('User is not assigned to this institution');
    }

    await this.prisma.userInstitution.deleteMany({
      where: {
        userId,
        institutionId,
      },
    });
  }

  async getInstitutions(userId: string) {
    return this.prisma.userInstitution.findMany({
      where: { userId },
      include: {
        institution: true,
      },
    });
  }

  async count(where?: Prisma.UserWhereInput): Promise<number> {
    return this.prisma.user.count({
      where: {
        ...where,
        deletedAt: null,
      },
    });
  }

  // Lifecycle transitions
  async activate(id: string): Promise<User> {
    const user = await this.prisma.user.findFirst({
      where: { id, deletedAt: null },
    });
    if (!user) throw new Error('User not found');
    if (user.status !== 'INVITED') {
      throw new Error(`Cannot activate user in ${user.status} status`);
    }

    return this.prisma.user.update({
      where: { id },
      data: { status: 'ACTIVE' },
    });
  }

  async suspend(id: string): Promise<User> {
    const user = await this.prisma.user.findFirst({
      where: { id, deletedAt: null },
    });
    if (!user) throw new Error('User not found');
    if (user.status !== 'ACTIVE') {
      throw new Error(`Cannot suspend user in ${user.status} status`);
    }

    return this.prisma.user.update({
      where: { id },
      data: { status: 'SUSPENDED' },
    });
  }

  async reactivate(id: string): Promise<User> {
    const user = await this.prisma.user.findFirst({
      where: { id, deletedAt: null },
    });
    if (!user) throw new Error('User not found');
    if (user.status !== 'SUSPENDED') {
      throw new Error(`Cannot reactivate user in ${user.status} status`);
    }

    return this.prisma.user.update({
      where: { id },
      data: { status: 'ACTIVE' },
    });
  }

  async archive(id: string): Promise<User> {
    const user = await this.prisma.user.findFirst({
      where: { id, deletedAt: null },
    });
    if (!user) throw new Error('User not found');
    if (user.status === 'ARCHIVED') {
      throw new Error('User is already archived');
    }

    return this.prisma.user.update({
      where: { id },
      data: { status: 'ARCHIVED', deletedAt: new Date() },
    });
  }

  async getByStatus(tenantId: string, status: UserStatus): Promise<User[]> {
    return this.prisma.user.findMany({
      where: { tenantId, status, deletedAt: null },
      include: {
        profile: true,
      },
    });
  }
}
