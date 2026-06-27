import prisma from '@school-erp/database';
import { NotFoundError, AcademicYearStatus } from '@school-erp/shared';

export interface CreateLevelDefInput {
  tenantId: string;
  name: string;
  displayOrder: number;
  isRequired: boolean;
}

export interface CreateLevelInstanceInput {
  tenantId: string;
  levelDefId: string;
  name: string;
  parentId?: string;
}

export interface AssignClassTeacherInput {
  userId: string;
  levelInstanceId: string;
  tenantId: string;
}

export interface AssignSubjectTeacherInput {
  userId: string;
  subjectId: string;
  levelInstanceId: string;
  tenantId: string;
}

export interface PromoteStudentsInput {
  studentIds: string[];
  targetLevelInstanceId: string;
  academicYearId: string;
  tenantId: string;
}

export class AcademicService {
  constructor(private db = prisma) {}

  // Level Definitions ─────────────────────────────────

  async createLevelDefinition(input: CreateLevelDefInput) {
    return this.db.levelDefinition.create({ data: input });
  }

  async getLevelDefinitions(tenantId: string) {
    return this.db.levelDefinition.findMany({
      where: { tenantId },
      orderBy: { displayOrder: 'asc' },
    });
  }

  // Level Instances ───────────────────────────────────

  async createLevelInstance(input: CreateLevelInstanceInput) {
    if (input.parentId) {
      const parent = await this.db.levelInstance.findUnique({ where: { id: input.parentId } });
      if (!parent) throw new NotFoundError('Parent level instance not found');
    }
    return this.db.levelInstance.create({ data: input });
  }

  async getLevelInstances(tenantId: string, parentId?: string) {
    return this.db.levelInstance.findMany({
      where: { tenantId, parentId: parentId ?? null, isActive: true },
    });
  }

  async getLevelInstanceTree(tenantId: string) {
    const roots = await this.db.levelInstance.findMany({
      where: { tenantId, parentId: null, isActive: true },
      include: { children: { include: { children: true } } },
    });
    return roots;
  }

  async getStudentsInLevelInstance(levelInstanceId: string, academicYearId: string, tenantId: string) {
    const enrollments = await this.db.studentEnrollment.findMany({
      where: { levelInstanceId, academicYearId, tenantId },
      include: { student: true },
    });
    return enrollments.map(e => e.student);
  }

  // Subjects ──────────────────────────────────────────

  async createSubject(tenantId: string, name: string, code?: string) {
    return this.db.subject.create({ data: { tenantId, name, code } });
  }

  async getSubjects(tenantId: string) {
    return this.db.subject.findMany({ where: { tenantId } });
  }

  // Academic Years ────────────────────────────────────

  async createAcademicYear(tenantId: string, name: string, startDate: Date, endDate: Date) {
    return this.db.academicYear.create({
      data: { tenantId, name, startDate, endDate },
    });
  }

  async activateAcademicYear(id: string, tenantId: string) {
    await this.db.academicYear.updateMany({
      where: { tenantId, status: 'ACTIVE' },
      data: { status: 'COMPLETED' },
    });
    return this.db.academicYear.update({
      where: { id },
      data: { status: 'ACTIVE' },
    });
  }

  async getAcademicYears(tenantId: string) {
    return this.db.academicYear.findMany({
      where: { tenantId },
      orderBy: { startDate: 'desc' },
    });
  }

  async getActiveAcademicYear(tenantId: string) {
    const year = await this.db.academicYear.findFirst({
      where: { tenantId, status: 'ACTIVE' },
    });
    if (!year) throw new NotFoundError('No active academic year');
    return year;
  }

  // Teacher Assignments ───────────────────────────────

  async assignClassTeacher(input: AssignClassTeacherInput) {
    return this.db.classTeacher.create({ data: input });
  }

  async removeClassTeacher(id: string) {
    return this.db.classTeacher.delete({ where: { id } });
  }

  async getClassTeachers(levelInstanceId: string) {
    return this.db.classTeacher.findMany({
      where: { levelInstanceId },
      include: { user: true },
    });
  }

  async assignSubjectTeacher(input: AssignSubjectTeacherInput) {
    return this.db.subjectTeacher.create({ data: input });
  }

  async removeSubjectTeacher(id: string) {
    return this.db.subjectTeacher.delete({ where: { id } });
  }

  async getSubjectTeachers(subjectId: string) {
    return this.db.subjectTeacher.findMany({
      where: { subjectId },
      include: { user: true, section: true },
    });
  }

  // Student Enrollment & Promotion ────────────────────

  async enrollStudent(studentId: string, levelInstanceId: string, academicYearId: string, tenantId: string, rollNumber?: number) {
    return this.db.studentEnrollment.create({
      data: { studentId, levelInstanceId, academicYearId, tenantId, rollNumber },
    });
  }

  async promoteStudents(input: PromoteStudentsInput) {
    const results = [];
    for (const studentId of input.studentIds) {
      const enrollment = await this.db.studentEnrollment.upsert({
        where: { studentId_academicYearId: { studentId, academicYearId: input.academicYearId } },
        update: { levelInstanceId: input.targetLevelInstanceId },
        create: {
          studentId,
          levelInstanceId: input.targetLevelInstanceId,
          academicYearId: input.academicYearId,
          tenantId: input.tenantId,
        },
      });
      results.push(enrollment);
    }
    return results;
  }
}
