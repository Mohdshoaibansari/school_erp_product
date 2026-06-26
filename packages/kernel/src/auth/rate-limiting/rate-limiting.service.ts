import { PrismaClient, AccountLockout } from '@school-erp/database';

export interface CheckLockoutInput {
  tenantId: string;
  userId: string;
}

export interface RecordAttemptInput {
  tenantId: string;
  email: string;
  ipAddress?: string;
  success: boolean;
}

export interface LockAccountInput {
  tenantId: string;
  userId: string;
  durationMinutes: number;
  reason?: string;
}

export class RateLimitingService {
  private readonly defaultMaxAttempts = 5;
  private readonly defaultLockoutMinutes = 15;

  constructor(private prisma: PrismaClient) {}

  async isAccountLocked(input: CheckLockoutInput): Promise<boolean> {
    const { tenantId, userId } = input;

    const lockout = await this.prisma.accountLockout.findFirst({
      where: {
        tenantId,
        userId,
        unlockedAt: null,
        expiresAt: { gt: new Date() },
      },
    });

    return !!lockout;
  }

  async getLockoutInfo(
    tenantId: string,
    userId: string
  ): Promise<{ isLocked: boolean; expiresAt?: Date; reason?: string }> {
    const lockout = await this.prisma.accountLockout.findFirst({
      where: {
        tenantId,
        userId,
        unlockedAt: null,
        expiresAt: { gt: new Date() },
      },
    });

    if (!lockout) {
      return { isLocked: false };
    }

    return {
      isLocked: true,
      expiresAt: lockout.expiresAt,
      reason: lockout.reason || undefined,
    };
  }

  async recordAttempt(input: RecordAttemptInput): Promise<void> {
    const { tenantId, email, ipAddress, success } = input;

    await this.prisma.loginAttempt.create({
      data: {
        tenantId,
        email,
        ipAddress,
        success,
      },
    });
  }

  async getFailedAttemptCount(
    tenantId: string,
    email: string,
    windowMinutes: number = 15
  ): Promise<number> {
    const windowStart = new Date();
    windowStart.setMinutes(windowStart.getMinutes() - windowMinutes);

    return this.prisma.loginAttempt.count({
      where: {
        tenantId,
        email,
        success: false,
        createdAt: { gte: windowStart },
      },
    });
  }

  async shouldLockAccount(
    tenantId: string,
    email: string,
    maxAttempts?: number
  ): Promise<boolean> {
    const threshold = maxAttempts || this.defaultMaxAttempts;
    const failedCount = await this.getFailedAttemptCount(tenantId, email);
    return failedCount >= threshold;
  }

  async lockAccount(input: LockAccountInput): Promise<AccountLockout> {
    const { tenantId, userId, durationMinutes, reason } = input;

    // Unlock any existing lockouts
    await this.prisma.accountLockout.updateMany({
      where: {
        tenantId,
        userId,
        unlockedAt: null,
      },
      data: {
        unlockedAt: new Date(),
      },
    });

    // Create new lockout
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + durationMinutes);

    return this.prisma.accountLockout.create({
      data: {
        tenantId,
        userId,
        expiresAt,
        reason,
      },
    });
  }

  async unlockAccount(tenantId: string, userId: string): Promise<void> {
    await this.prisma.accountLockout.updateMany({
      where: {
        tenantId,
        userId,
        unlockedAt: null,
      },
      data: {
        unlockedAt: new Date(),
      },
    });
  }

  async cleanupExpiredLockouts(): Promise<number> {
    const result = await this.prisma.accountLockout.deleteMany({
      where: {
        expiresAt: { lt: new Date() },
      },
    });

    return result.count;
  }

  async getRecentAttempts(
    tenantId: string,
    email: string,
    limit: number = 10
  ) {
    return this.prisma.loginAttempt.findMany({
      where: {
        tenantId,
        email,
      },
      orderBy: { createdAt: 'desc' },
      take: limit,
    });
  }
}
