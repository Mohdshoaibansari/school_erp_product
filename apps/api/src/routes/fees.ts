import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { authorize } from '../middleware/authorize';
import { requireTenant } from '../middleware/require-tenant';
import { FeeService } from '@school-erp/fees';
import { AcademicService } from '@school-erp/kernel';

const academicService = new AcademicService();
const feeService = new FeeService(academicService);

export default async function routes(fastify: FastifyInstance) {
  fastify.post('/fees/structures', {
    preHandler: [requireTenant, authorize('fees:*')],
    schema: {
      description: 'Create a fee structure for a level instance',
      response: { 201: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as {
      levelInstanceId: string;
      academicYearId: string;
      name: string;
      amount: number;
    };
    const structure = await feeService.createFeeStructure(
      tenantId,
      body.levelInstanceId,
      body.academicYearId,
      body.name,
      body.amount,
    );
    reply.status(201).send(structure);
  });

  fastify.get('/fees/structures', {
    preHandler: [requireTenant],
    schema: {
      description: 'Get fee structures, optionally filtered by level instance',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { levelInstanceId } = request.query as { levelInstanceId?: string };
    const structures = await feeService.getFeeStructures(tenantId, levelInstanceId);
    reply.send(structures);
  });

  fastify.post('/fees/payments', {
    preHandler: [requireTenant, authorize('fees:*')],
    schema: {
      description: 'Record a fee payment for a student',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as {
      studentId: string;
      feeStructureId: string;
      amount: number;
      paymentMethod?: string;
    };
    const payment = await feeService.recordPayment(
      body.studentId,
      body.feeStructureId,
      body.amount,
      request.userId,
      tenantId,
      body.paymentMethod,
    );
    reply.send(payment);
  });

  fastify.get('/fees/payments', {
    preHandler: [requireTenant],
    schema: {
      description: 'Get fee payments, optionally filtered by student',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { studentId } = request.query as { studentId?: string };
    const payments = await feeService.getPayments(tenantId, studentId);
    reply.send(payments);
  });

  fastify.get('/fees/pending-dues', {
    preHandler: [requireTenant],
    schema: {
      description: 'Get pending fee dues, optionally filtered by level instance',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { levelInstanceId } = request.query as { levelInstanceId?: string };
    const dues = await feeService.getPendingDues(tenantId, levelInstanceId);
    reply.send(dues);
  });
}
