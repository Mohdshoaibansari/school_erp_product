import prisma from '@school-erp/database';
import type { AcademicService, PromoteStudentsInput } from '@school-erp/kernel';
import type { SubscriptionService } from '@school-erp/kernel';
import { NotFoundError, ValidationError } from '@school-erp/shared';

interface CreateStudentInput {
  tenantId: string;
  firstName: string;
  lastName?: string;
  dateOfBirth?: Date;
  gender?: string;
  guardianName?: string;
  guardianPhone?: string;
  levelInstanceId: string;
  academicYearId: string;
}

interface BulkImportRow {
  firstName: string;
  lastName?: string;
  dateOfBirth?: Date;
  gender?: string;
  guardianName?: string;
  guardianPhone?: string;
}

interface BulkImportResult {
  total: number;
  succeeded: number;
  failed: number;
  errors: Array<{ row: number; message: string }>;
}

export class StudentService {
  constructor(
    private academic: AcademicService,
    private subscription: SubscriptionService,
  ) {}

  async createStudent(input: CreateStudentInput) {
    if (!input.firstName || input.firstName.trim().length === 0) {
      throw new ValidationError('firstName is required');
    }

    await this.subscription.checkStudentLimit(input.tenantId);

    const student = await prisma.student.create({
      data: {
        tenantId: input.tenantId,
        firstName: input.firstName.trim(),
        lastName: input.lastName,
        dateOfBirth: input.dateOfBirth,
        gender: input.gender,
      },
    });

    if (input.guardianName) {
      await prisma.studentParent.create({
        data: {
          studentId: student.id,
          parentName: input.guardianName,
          phone: input.guardianPhone,
          tenantId: input.tenantId,
        },
      });
    }

    await this.academic.enrollStudent(
      student.id,
      input.levelInstanceId,
      input.academicYearId,
      input.tenantId,
    );

    return student;
  }

  async bulkImport(
    tenantId: string,
    students: BulkImportRow[],
    levelInstanceId: string,
    academicYearId: string,
  ): Promise<BulkImportResult> {
    const result: BulkImportResult = {
      total: students.length,
      succeeded: 0,
      failed: 0,
      errors: [],
    };

    for (let i = 0; i < students.length; i++) {
      try {
        await this.createStudent({
          ...students[i],
          tenantId,
          levelInstanceId,
          academicYearId,
        });
        result.succeeded++;
      } catch (err) {
        result.failed++;
        result.errors.push({
          row: i,
          message: err instanceof Error ? err.message : 'Unknown error',
        });
      }
    }

    return result;
  }

  async updateProfile(
    studentId: string,
    updates: {
      firstName?: string;
      lastName?: string;
      dateOfBirth?: Date;
      gender?: string;
    },
  ) {
    const student = await prisma.student.findUnique({
      where: { id: studentId },
    });
    if (!student) {
      throw new NotFoundError('Student not found');
    }

    return prisma.student.update({
      where: { id: studentId },
      data: updates,
    });
  }

  async getById(studentId: string) {
    const student = await prisma.student.findUnique({
      where: { id: studentId },
      include: {
        enrollments: true,
        feePayments: true,
      },
    });
    if (!student) {
      throw new NotFoundError('Student not found');
    }
    return student;
  }

  async promoteStudents(input: PromoteStudentsInput) {
    return this.academic.promoteStudents(input);
  }

  async updateStatus(studentId: string, status: string) {
    const student = await prisma.student.findUnique({
      where: { id: studentId },
    });
    if (!student) {
      throw new NotFoundError('Student not found');
    }

    return prisma.student.update({
      where: { id: studentId },
      data: { status },
    });
  }
}
