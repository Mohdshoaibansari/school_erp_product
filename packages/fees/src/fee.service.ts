import prisma from '@school-erp/database';
import { NotFoundError, generateReceiptNumber } from '@school-erp/shared';
import { AcademicService } from '@school-erp/kernel';

export class FeeService {
  constructor(private academic: AcademicService) {}

  async createFeeStructure(
    tenantId: string,
    levelInstanceId: string,
    academicYearId: string,
    name: string,
    amount: number,
  ) {
    return prisma.feeStructure.create({
      data: { tenantId, levelInstanceId, academicYearId, name, amount },
    });
  }

  async getFeeStructures(tenantId: string, levelInstanceId?: string) {
    return prisma.feeStructure.findMany({
      where: { tenantId, ...(levelInstanceId ? { levelInstanceId } : {}) },
    });
  }

  async recordPayment(
    studentId: string,
    feeStructureId: string,
    amount: number,
    receivedBy: string,
    tenantId: string,
    paymentMethod?: string,
  ) {
    const structure = await prisma.feeStructure.findUnique({
      where: { id: feeStructureId },
    });
    if (!structure) throw new NotFoundError('Fee structure not found');

    return prisma.feePayment.create({
      data: {
        studentId,
        feeStructureId,
        amount,
        receivedBy,
        tenantId,
        paymentMethod,
        receiptId: generateReceiptNumber(),
      },
    });
  }

  async getPayments(tenantId: string, studentId?: string) {
    return prisma.feePayment.findMany({
      where: { tenantId, ...(studentId ? { studentId } : {}) },
      include: { student: true, feeStructure: true },
    });
  }

  async getPendingDues(tenantId: string, levelInstanceId?: string) {
    const structures = await this.getFeeStructures(tenantId, levelInstanceId);

    const studentIds = levelInstanceId
      ? (await this.academic.getStudentsInLevelInstance(levelInstanceId, '', tenantId)).map(s => s.id)
      : (await prisma.student.findMany({ where: { tenantId, status: 'ACTIVE' }, select: { id: true } })).map(s => s.id);

    const payments = await prisma.feePayment.findMany({
      where: { studentId: { in: studentIds }, tenantId },
    });

    const paymentByStudent = new Map<string, number>();
    for (const p of payments) {
      paymentByStudent.set(p.studentId, (paymentByStudent.get(p.studentId) ?? 0) + p.amount);
    }

    const totalExpected = structures.reduce((sum, s) => sum + s.amount, 0);

    const report = studentIds.map(studentId => {
      const paid = paymentByStudent.get(studentId) ?? 0;
      return { studentId, paid, balance: totalExpected - paid };
    });

    return { totalExpectedPerStudent: totalExpected, structures, report };
  }
}
