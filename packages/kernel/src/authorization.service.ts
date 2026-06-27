import prisma from '@school-erp/database';
import { NotFoundError, UnauthorizedError, UserRole } from '@school-erp/shared';

const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  SUPER_ADMIN: ['*'],
  SCHOOL_ADMIN: ['*'],
  PRINCIPAL: ['attendance:*', 'students:*', 'fees:*', 'timetable:*', 'exams:*'],
  TEACHER: ['attendance:mark', 'attendance:view', 'students:view', 'exams:enter_marks'],
  ACCOUNTANT: ['fees:*', 'students:view'],
};

export class AuthorizationService {
  constructor(private db = prisma) {}

  async checkPermission(userId: string, tenantId: string, permission: string): Promise<boolean> {
    const membership = await this.db.userTenant.findUnique({
      where: { userId_tenantId: { userId, tenantId } },
    });
    if (!membership) return false;

    const rolePermissions = ROLE_PERMISSIONS[membership.role as UserRole] ?? [];
    if (rolePermissions.includes('*')) return true;

    return rolePermissions.some(p => {
      if (p.endsWith(':*')) {
        return permission.startsWith(p.replace(':*', ''));
      }
      return p === permission;
    });
  }

  async enforcePermission(userId: string, tenantId: string, permission: string): Promise<void> {
    const allowed = await this.checkPermission(userId, tenantId, permission);
    if (!allowed) throw new UnauthorizedError();
  }

  async getClassTeacherScope(teacherId: string) {
    const assignments = await this.db.classTeacher.findMany({
      where: { userId: teacherId },
      select: { levelInstanceId: true },
    });
    return assignments.map(a => a.levelInstanceId);
  }

  async getSubjectTeacherScope(teacherId: string, subjectId?: string) {
    const where: Record<string, unknown> = { userId: teacherId };
    if (subjectId) where.subjectId = subjectId;

    const assignments = await this.db.subjectTeacher.findMany({
      where,
      select: { levelInstanceId: true, subjectId: true },
    });
    return assignments;
  }
}
