import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { authorize } from '../middleware/authorize';
import { requireTenant } from '../middleware/require-tenant';
import { requireModule } from '../middleware/module-gate';
import { ExamService } from '@school-erp/exams';
import { SubscriptionService, AuthorizationService } from '@school-erp/kernel';

const subscriptionService = new SubscriptionService();
const authzService = new AuthorizationService();
const examService = new ExamService(subscriptionService, authzService);

export default async function routes(fastify: FastifyInstance) {
  fastify.post('/exams/schedules', {
    preHandler: [requireTenant, requireModule('exams'), authorize('exams:*')],
    schema: {
      description: 'Create an exam schedule',
      response: { 201: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as {
      name: string;
      levelInstanceId: string;
      subjectId: string;
      examDate: string;
      maxMarks: number;
      academicYearId: string;
    };
    const schedule = await examService.createSchedule(
      tenantId,
      body.name,
      body.levelInstanceId,
      body.subjectId,
      new Date(body.examDate),
      body.maxMarks,
      body.academicYearId,
    );
    reply.status(201).send(schedule);
  });

  fastify.get('/exams/schedules', {
    preHandler: [requireTenant, requireModule('exams')],
    schema: {
      description: 'Get exam schedules, optionally filtered by level instance',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { levelInstanceId } = request.query as { levelInstanceId?: string };
    const schedules = await examService.getSchedules(tenantId, levelInstanceId);
    reply.send(schedules);
  });

  fastify.post('/exams/marks', {
    preHandler: [requireTenant, requireModule('exams'), authorize('exams:enter_marks')],
    schema: {
      description: 'Enter marks for students in an exam schedule',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as {
      examScheduleId: string;
      entries: Array<{ studentId: string; marksObtained: number }>;
    };
    const marks = await examService.enterMarks(
      request.userId,
      tenantId,
      body.examScheduleId,
      body.entries,
    );
    reply.send(marks);
  });

  fastify.get('/exams/marks/:examScheduleId', {
    preHandler: [requireTenant, requireModule('exams')],
    schema: {
      description: 'Get marks for an exam schedule',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { examScheduleId } = request.params as { examScheduleId: string };
    const marks = await examService.getMarks(tenantId, examScheduleId);
    reply.send(marks);
  });

  fastify.get('/exams/report-card/:studentId', {
    preHandler: [requireTenant, requireModule('exams')],
    schema: {
      description: 'Generate report card for a student in an academic year',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { studentId } = request.params as { studentId: string };
    const { academicYearId } = request.query as { academicYearId: string };
    const reportCard = await examService.generateReportCard(
      tenantId,
      studentId,
      academicYearId,
    );
    reply.send(reportCard);
  });
}
