import { PrismaClient, AuditLog, Prisma } from '@school-erp/database';

export interface LogAuditInput {
  tenantId: string;
  institutionId?: string;
  userId?: string;
  action: string;
  entityType: string;
  entityId?: string;
  details?: Record<string, any>;
  ipAddress?: string;
}

export interface QueryAuditOptions {
  tenantId: string;
  institutionId?: string;
  userId?: string;
  entityType?: string;
  entityId?: string;
  action?: string;
  startDate?: Date;
  endDate?: Date;
  skip?: number;
  take?: number;
}

export class AuditService {
  constructor(private prisma: PrismaClient) {}

  async log(input: LogAuditInput): Promise<AuditLog> {
    return this.prisma.auditLog.create({
      data: {
        tenantId: input.tenantId,
        institutionId: input.institutionId,
        userId: input.userId,
        action: input.action,
        entityType: input.entityType,
        entityId: input.entityId,
        details: input.details,
        ipAddress: input.ipAddress,
      },
    });
  }

  async query(options: QueryAuditOptions): Promise<AuditLog[]> {
    const {
      tenantId,
      institutionId,
      userId,
      entityType,
      entityId,
      action,
      startDate,
      endDate,
      skip = 0,
      take = 50,
    } = options;

    return this.prisma.auditLog.findMany({
      where: {
        tenantId,
        ...(institutionId ? { institutionId } : {}),
        ...(userId ? { userId } : {}),
        ...(entityType ? { entityType } : {}),
        ...(entityId ? { entityId } : {}),
        ...(action ? { action } : {}),
        ...(startDate || endDate
          ? {
              createdAt: {
                ...(startDate ? { gte: startDate } : {}),
                ...(endDate ? { lte: endDate } : {}),
              },
            }
          : {}),
      },
      skip,
      take,
      orderBy: { createdAt: 'desc' },
    });
  }

  async count(options: QueryAuditOptions): Promise<number> {
    const {
      tenantId,
      institutionId,
      userId,
      entityType,
      entityId,
      action,
      startDate,
      endDate,
    } = options;

    return this.prisma.auditLog.count({
      where: {
        tenantId,
        ...(institutionId ? { institutionId } : {}),
        ...(userId ? { userId } : {}),
        ...(entityType ? { entityType } : {}),
        ...(entityId ? { entityId } : {}),
        ...(action ? { action } : {}),
        ...(startDate || endDate
          ? {
              createdAt: {
                ...(startDate ? { gte: startDate } : {}),
                ...(endDate ? { lte: endDate } : {}),
              },
            }
          : {}),
      },
    });
  }

  async getEntityHistory(
    tenantId: string,
    entityType: string,
    entityId: string
  ): Promise<AuditLog[]> {
    return this.prisma.auditLog.findMany({
      where: {
        tenantId,
        entityType,
        entityId,
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  async getUserActivity(
    tenantId: string,
    userId: string,
    options: { skip?: number; take?: number } = {}
  ): Promise<AuditLog[]> {
    const { skip = 0, take = 50 } = options;

    return this.prisma.auditLog.findMany({
      where: {
        tenantId,
        userId,
      },
      skip,
      take,
      orderBy: { createdAt: 'desc' },
    });
  }
}
