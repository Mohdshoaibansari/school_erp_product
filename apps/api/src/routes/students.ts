import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { authorize } from '../middleware/authorize';
import { requireTenant } from '../middleware/require-tenant';
import { StudentService } from '@school-erp/students';
import { AcademicService, SubscriptionService } from '@school-erp/kernel';

const academicService = new AcademicService();
const subscriptionService = new SubscriptionService();
const studentService = new StudentService(academicService, subscriptionService);

export default async function routes(fastify: FastifyInstance) {
  fastify.post('/students', {
    preHandler: [requireTenant, authorize('students:*')],
    schema: {
      description: 'Create a new student and enroll in a level instance',
      response: { 201: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as Record<string, any>;
    const student = await studentService.createStudent({
      tenantId,
      firstName: body.firstName,
      lastName: body.lastName,
      dateOfBirth: body.dateOfBirth ? new Date(body.dateOfBirth) : undefined,
      gender: body.gender,
      guardianName: body.guardianName,
      guardianPhone: body.guardianPhone,
      levelInstanceId: body.levelInstanceId,
      academicYearId: body.academicYearId,
    });
    reply.status(201).send(student);
  });

  fastify.post('/students/bulk-import', {
    preHandler: [requireTenant, authorize('students:*')],
    schema: {
      description: 'Bulk import students into a level instance',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as {
      students: any[];
      levelInstanceId: string;
      academicYearId: string;
    };
    const result = await studentService.bulkImport(
      tenantId,
      body.students,
      body.levelInstanceId,
      body.academicYearId,
    );
    reply.send(result);
  });

  fastify.get('/students/:id', {
    preHandler: [requireTenant],
    schema: {
      description: 'Get student by ID with enrollments and fee payments',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const { id } = request.params as { id: string };
    const student = await studentService.getById(id);
    reply.send(student);
  });

  fastify.patch('/students/:id', {
    preHandler: [requireTenant, authorize('students:*')],
    schema: {
      description: 'Update student profile',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const { id } = request.params as { id: string };
    const body = request.body as Record<string, any>;
    const student = await studentService.updateProfile(id, {
      firstName: body.firstName,
      lastName: body.lastName,
      dateOfBirth: body.dateOfBirth ? new Date(body.dateOfBirth) : undefined,
      gender: body.gender,
    });
    reply.send(student);
  });

  fastify.post('/students/promote', {
    preHandler: [requireTenant, authorize('students:*')],
    schema: {
      description: 'Promote students to a target level instance',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as {
      studentIds: string[];
      targetLevelInstanceId: string;
      academicYearId: string;
    };
    const result = await studentService.promoteStudents({
      studentIds: body.studentIds,
      targetLevelInstanceId: body.targetLevelInstanceId,
      academicYearId: body.academicYearId,
      tenantId,
    });
    reply.send(result);
  });

  fastify.patch('/students/:id/status', {
    preHandler: [requireTenant, authorize('students:*')],
    schema: {
      description: 'Update student status',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const { id } = request.params as { id: string };
    const { status } = request.body as { status: string };
    const student = await studentService.updateStatus(id, status);
    reply.send(student);
  });
}
