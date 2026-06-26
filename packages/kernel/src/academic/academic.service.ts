import { PrismaClient, AcademicYear, Term, OrgUnit } from '@school-erp/database';

export interface CreateAcademicYearInput {
  name: string;
  startDate: Date;
  endDate: Date;
}

export interface CreateTermInput {
  academicYearId: string;
  name: string;
  startDate: Date;
  endDate: Date;
}

export class AcademicService {
  constructor(private prisma: PrismaClient) {}

  async createAcademicYear(
    institutionId: string,
    data: CreateAcademicYearInput
  ): Promise<AcademicYear> {
    // Validate dates
    if (data.startDate >= data.endDate) {
      throw new Error('Start date must be before end date');
    }

    // Check for overlapping years
    const overlapping = await this.prisma.academicYear.findFirst({
      where: {
        institutionId,
        deletedAt: null,
        OR: [
          {
            startDate: { lte: data.endDate },
            endDate: { gte: data.startDate },
          },
        ],
      },
    });

    if (overlapping) {
      throw new Error('Academic year overlaps with existing year');
    }

    // Check if this is the current year
    const now = new Date();
    const isCurrent = now >= data.startDate && now <= data.endDate;

    return this.prisma.academicYear.create({
      data: {
        institutionId,
        name: data.name,
        startDate: data.startDate,
        endDate: data.endDate,
        isCurrent,
        status: isCurrent ? 'ACTIVE' : 'UPCOMING',
      },
    });
  }

  async getCurrentYear(institutionId: string): Promise<AcademicYear | null> {
    return this.prisma.academicYear.findFirst({
      where: {
        institutionId,
        isCurrent: true,
        deletedAt: null,
      },
      include: {
        terms: true,
      },
    });
  }

  async getAcademicYears(institutionId: string): Promise<AcademicYear[]> {
    return this.prisma.academicYear.findMany({
      where: {
        institutionId,
        deletedAt: null,
      },
      orderBy: { startDate: 'desc' },
      include: {
        terms: true,
      },
    });
  }

  async createTerm(data: CreateTermInput): Promise<Term> {
    // Validate academic year exists
    const academicYear = await this.prisma.academicYear.findFirst({
      where: {
        id: data.academicYearId,
        deletedAt: null,
      },
    });

    if (!academicYear) {
      throw new Error('Academic year not found');
    }

    // Validate dates are within academic year
    if (data.startDate < academicYear.startDate || data.endDate > academicYear.endDate) {
      throw new Error('Term dates must be within academic year dates');
    }

    // Check if this is the current term
    const now = new Date();
    const isCurrent = now >= data.startDate && now <= data.endDate;

    return this.prisma.term.create({
      data: {
        academicYearId: data.academicYearId,
        name: data.name,
        startDate: data.startDate,
        endDate: data.endDate,
        isCurrent,
      },
    });
  }

  async getCurrentTerm(institutionId: string): Promise<Term | null> {
    const currentYear = await this.getCurrentYear(institutionId);
    if (!currentYear) {
      return null;
    }

    return this.prisma.term.findFirst({
      where: {
        academicYearId: currentYear.id,
        isCurrent: true,
      },
    });
  }

  async getGrades(institutionId: string): Promise<OrgUnit[]> {
    return this.prisma.orgUnit.findMany({
      where: {
        institutionId,
        type: 'GRADE',
        deletedAt: null,
      },
      orderBy: { name: 'asc' },
    });
  }

  async getClasses(institutionId: string, gradeId?: string): Promise<OrgUnit[]> {
    return this.prisma.orgUnit.findMany({
      where: {
        institutionId,
        type: 'CLASS',
        deletedAt: null,
        ...(gradeId ? { parentId: gradeId } : {}),
      },
      orderBy: { name: 'asc' },
      include: {
        parent: true,
        children: true,
      },
    });
  }

  async getSections(institutionId: string, classId?: string): Promise<OrgUnit[]> {
    return this.prisma.orgUnit.findMany({
      where: {
        institutionId,
        type: 'SECTION',
        deletedAt: null,
        ...(classId ? { parentId: classId } : {}),
      },
      orderBy: { name: 'asc' },
      include: {
        parent: true,
      },
    });
  }
}
