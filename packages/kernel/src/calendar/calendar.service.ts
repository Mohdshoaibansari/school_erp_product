import { PrismaClient, CalendarEvent, CalendarEventType } from '@school-erp/database';

export interface CreateCalendarEventInput {
  date: Date;
  type: CalendarEventType;
  label?: string;
  description?: string;
}

export interface GetEventsOptions {
  startDate?: Date;
  endDate?: Date;
  type?: CalendarEventType;
}

export class CalendarService {
  constructor(private prisma: PrismaClient) {}

  async createEvent(
    institutionId: string,
    data: CreateCalendarEventInput
  ): Promise<CalendarEvent> {
    // Check for existing event on the same date with the same type
    const existing = await this.prisma.calendarEvent.findFirst({
      where: {
        institutionId,
        date: data.date,
        type: data.type,
      },
    });

    if (existing) {
      throw new Error(`Event of type ${data.type} already exists for this date`);
    }

    return this.prisma.calendarEvent.create({
      data: {
        institutionId,
        date: data.date,
        type: data.type,
        label: data.label,
        description: data.description,
      },
    });
  }

  async getToday(institutionId: string): Promise<CalendarEvent | null> {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    return this.prisma.calendarEvent.findFirst({
      where: {
        institutionId,
        date: {
          gte: today,
          lt: tomorrow,
        },
      },
    });
  }

  async getDayType(institutionId: string, date: Date): Promise<CalendarEventType | null> {
    const startOfDay = new Date(date);
    startOfDay.setHours(0, 0, 0, 0);

    const endOfDay = new Date(startOfDay);
    endOfDay.setDate(endOfDay.getDate() + 1);

    const event = await this.prisma.calendarEvent.findFirst({
      where: {
        institutionId,
        date: {
          gte: startOfDay,
          lt: endOfDay,
        },
      },
    });

    return event?.type || null;
  }

  async isHoliday(institutionId: string, date: Date): Promise<boolean> {
    const dayType = await this.getDayType(institutionId, date);
    return dayType === 'HOLIDAY';
  }

  async isSchoolDay(institutionId: string, date: Date): Promise<boolean> {
    const dayType = await this.getDayType(institutionId, date);
    return dayType === 'SCHOOL_DAY' || dayType === 'EXAM_DAY';
  }

  async getEventsInRange(
    institutionId: string,
    options: GetEventsOptions
  ): Promise<CalendarEvent[]> {
    const { startDate, endDate, type } = options;

    return this.prisma.calendarEvent.findMany({
      where: {
        institutionId,
        ...(startDate && endDate
          ? {
              date: {
                gte: startDate,
                lte: endDate,
              },
            }
          : {}),
        ...(type ? { type } : {}),
      },
      orderBy: { date: 'asc' },
    });
  }

  async updateEvent(
    eventId: string,
    data: Partial<CreateCalendarEventInput>
  ): Promise<CalendarEvent> {
    const existing = await this.prisma.calendarEvent.findUnique({
      where: { id: eventId },
    });

    if (!existing) {
      throw new Error('Calendar event not found');
    }

    return this.prisma.calendarEvent.update({
      where: { id: eventId },
      data,
    });
  }

  async deleteEvent(eventId: string): Promise<void> {
    await this.prisma.calendarEvent.delete({
      where: { id: eventId },
    });
  }
}
