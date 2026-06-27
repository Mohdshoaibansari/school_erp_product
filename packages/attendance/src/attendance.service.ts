import { AuthorizationService, AcademicService } from '@school-erp/kernel';
import prisma from '@school-erp/database';
import { AttendanceStatus } from '@school-erp/shared';

interface AttendanceRecordInput {
  studentId: string;
  levelInstanceId: string;
  date: Date;
  status: AttendanceStatus;
}

export class AttendanceService {
  constructor(
    private authz: AuthorizationService,
    private academic: AcademicService,
  ) {}

  async markAttendance(
    teacherId: string,
    tenantId: string,
    records: AttendanceRecordInput[],
  ) {
    const scope = await this.authz.getClassTeacherScope(teacherId);

    for (const record of records) {
      if (!scope.includes(record.levelInstanceId)) {
        throw new Error('Teacher does not have access to this level instance');
      }
    }

    const results = [];
    for (const record of records) {
      const result = await prisma.attendanceRecord.upsert({
        where: {
          studentId_levelInstanceId_date: {
            studentId: record.studentId,
            levelInstanceId: record.levelInstanceId,
            date: record.date,
          },
        },
        update: {
          status: record.status,
          markedBy: teacherId,
        },
        create: {
          studentId: record.studentId,
          levelInstanceId: record.levelInstanceId,
          date: record.date,
          status: record.status,
          markedBy: teacherId,
          tenantId,
        },
      });
      results.push(result);
    }
    return results;
  }

  async markAllPresent(
    teacherId: string,
    tenantId: string,
    levelInstanceId: string,
    date: Date,
    studentIds: string[],
  ) {
    const scope = await this.authz.getClassTeacherScope(teacherId);
    if (!scope.includes(levelInstanceId)) {
      throw new Error('Teacher does not have access to this level instance');
    }

    const results = [];
    for (const studentId of studentIds) {
      const result = await prisma.attendanceRecord.upsert({
        where: {
          studentId_levelInstanceId_date: {
            studentId,
            levelInstanceId,
            date,
          },
        },
        update: {
          status: 'PRESENT',
          markedBy: teacherId,
        },
        create: {
          studentId,
          levelInstanceId,
          date,
          status: 'PRESENT',
          markedBy: teacherId,
          tenantId,
        },
      });
      results.push(result);
    }
    return results;
  }

  async getAttendanceByDate(levelInstanceId: string, date: Date, tenantId: string) {
    return prisma.attendanceRecord.findMany({
      where: { levelInstanceId, date, tenantId },
    });
  }

  async getMonthlyReport(
    levelInstanceId: string,
    startDate: Date,
    endDate: Date,
    tenantId: string,
  ) {
    const records = await prisma.attendanceRecord.findMany({
      where: {
        levelInstanceId,
        tenantId,
        date: { gte: startDate, lte: endDate },
      },
      orderBy: { date: 'asc' },
    });

    const grouped: Record<string, typeof records> = {};
    for (const record of records) {
      const key = record.date.toISOString().split('T')[0];
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(record);
    }
    return grouped;
  }
}
