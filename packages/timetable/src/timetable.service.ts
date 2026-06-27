import { SubscriptionService } from '@school-erp/kernel';
import prisma from '@school-erp/database';

export class TimetableService {
  constructor(private subscription: SubscriptionService) {}

  async createEntry(
    tenantId: string,
    levelInstanceId: string,
    subjectId: string,
    teacherId: string,
    dayOfWeek: number,
    periodNumber: number,
    room?: string,
  ) {
    await this.subscription.enforceModuleEnabled(tenantId, 'timetable');

    const conflict = await prisma.timetableEntry.findFirst({
      where: { tenantId, levelInstanceId, dayOfWeek, periodNumber },
    });

    if (conflict) {
      throw new Error(
        `Timetable conflict: ${levelInstanceId} already has an entry for day ${dayOfWeek} period ${periodNumber}`,
      );
    }

    return prisma.timetableEntry.create({
      data: {
        tenantId,
        levelInstanceId,
        subjectId,
        teacherId,
        dayOfWeek,
        periodNumber,
        room,
      },
    });
  }

  async getTimetable(tenantId: string, levelInstanceId: string) {
    return prisma.timetableEntry.findMany({
      where: { tenantId, levelInstanceId },
      orderBy: [{ dayOfWeek: 'asc' }, { periodNumber: 'asc' }],
    });
  }

  async getTeacherTimetable(tenantId: string, teacherId: string) {
    return prisma.timetableEntry.findMany({
      where: { tenantId, teacherId },
      orderBy: [{ dayOfWeek: 'asc' }, { periodNumber: 'asc' }],
    });
  }

  async deleteEntry(id: string) {
    return prisma.timetableEntry.delete({ where: { id } });
  }
}
