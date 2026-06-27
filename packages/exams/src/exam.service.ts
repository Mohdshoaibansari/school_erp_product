import { SubscriptionService, AuthorizationService } from '@school-erp/kernel';
import prisma from '@school-erp/database';
import { NotFoundError, ValidationError } from '@school-erp/shared';

export class ExamService {
  constructor(
    private subscription: SubscriptionService,
    private authz: AuthorizationService,
    private db = prisma,
  ) {}

  async createSchedule(
    tenantId: string,
    name: string,
    levelInstanceId: string,
    subjectId: string,
    examDate: Date,
    maxMarks: number,
    academicYearId: string,
  ) {
    await this.subscription.enforceModuleEnabled(tenantId, 'exams');
    return this.db.examSchedule.create({
      data: { tenantId, name, levelInstanceId, subjectId, examDate, maxMarks, academicYearId },
    });
  }

  async getSchedules(tenantId: string, levelInstanceId?: string) {
    return this.db.examSchedule.findMany({
      where: { tenantId, ...(levelInstanceId ? { levelInstanceId } : {}) },
    });
  }

  async enterMarks(
    teacherId: string,
    tenantId: string,
    examScheduleId: string,
    entries: Array<{ studentId: string; marksObtained: number }>,
  ) {
    const schedule = await this.db.examSchedule.findUnique({ where: { id: examScheduleId } });
    if (!schedule || schedule.tenantId !== tenantId) {
      throw new NotFoundError('Exam schedule not found');
    }

    const assignments = await this.authz.getSubjectTeacherScope(teacherId, schedule.subjectId);
    const assignedLevels = assignments.map(a => a.levelInstanceId);
    if (!assignedLevels.includes(schedule.levelInstanceId)) {
      throw new ValidationError('Teacher is not assigned to this subject for this level');
    }

    for (const entry of entries) {
      if (entry.marksObtained > schedule.maxMarks) {
        throw new ValidationError(
          `Marks (${entry.marksObtained}) exceed maximum marks (${schedule.maxMarks}) for student ${entry.studentId}`,
        );
      }
    }

    const results = [];
    for (const entry of entries) {
      const mark = await this.db.examMark.upsert({
        where: { studentId_examScheduleId: { studentId: entry.studentId, examScheduleId } },
        update: { marksObtained: entry.marksObtained, enteredBy: teacherId },
        create: {
          studentId: entry.studentId,
          examScheduleId,
          marksObtained: entry.marksObtained,
          enteredBy: teacherId,
          tenantId,
        },
      });
      results.push(mark);
    }
    return results;
  }

  async getMarks(tenantId: string, examScheduleId: string) {
    return this.db.examMark.findMany({
      where: { tenantId, examScheduleId },
      include: { student: true },
    });
  }

  async generateReportCard(tenantId: string, studentId: string, academicYearId: string) {
    const enrollment = await this.db.studentEnrollment.findUnique({
      where: { studentId_academicYearId: { studentId, academicYearId } },
    });
    if (!enrollment || enrollment.tenantId !== tenantId) {
      throw new NotFoundError('Student enrollment not found for this academic year');
    }

    const schedules = await this.db.examSchedule.findMany({
      where: { tenantId, levelInstanceId: enrollment.levelInstanceId, academicYearId },
      include: {
        marks: { where: { studentId }, include: { student: true } },
      },
    });

    const examResults = schedules.map(schedule => {
      const mark = schedule.marks[0] ?? null;
      return {
        scheduleId: schedule.id,
        examName: schedule.name,
        examDate: schedule.examDate,
        subjectId: schedule.subjectId,
        maxMarks: schedule.maxMarks,
        marksObtained: mark?.marksObtained ?? null,
        percentage: mark ? (mark.marksObtained / schedule.maxMarks) * 100 : null,
      };
    });

    const totalMaxMarks = examResults.reduce((sum, r) => sum + r.maxMarks, 0);
    const totalMarksObtained = examResults.reduce((sum, r) => sum + (r.marksObtained ?? 0), 0);

    return {
      studentId,
      academicYearId,
      levelInstanceId: enrollment.levelInstanceId,
      examResults,
      summary: totalMaxMarks > 0
        ? {
            totalMarksObtained,
            totalMaxMarks,
            overallPercentage: (totalMarksObtained / totalMaxMarks) * 100,
          }
        : null,
    };
  }
}
