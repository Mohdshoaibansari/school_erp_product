import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { authorize } from '../middleware/authorize';
import { requireTenant } from '../middleware/require-tenant';
import { requireModule } from '../middleware/module-gate';
import { TimetableService } from '@school-erp/timetable';
import { SubscriptionService } from '@school-erp/kernel';

const subscriptionService = new SubscriptionService();
const timetableService = new TimetableService(subscriptionService);

export default async function routes(fastify: FastifyInstance) {
  fastify.post('/timetable', {
    preHandler: [requireTenant, requireModule('timetable'), authorize('timetable:*')],
    schema: {
      description: 'Create a timetable entry',
      response: { 201: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as {
      levelInstanceId: string;
      subjectId: string;
      teacherId: string;
      dayOfWeek: number;
      periodNumber: number;
      room?: string;
    };
    const entry = await timetableService.createEntry(
      tenantId,
      body.levelInstanceId,
      body.subjectId,
      body.teacherId,
      body.dayOfWeek,
      body.periodNumber,
      body.room,
    );
    reply.status(201).send(entry);
  });

  fastify.get('/timetable/:levelInstanceId', {
    preHandler: [requireTenant, requireModule('timetable')],
    schema: {
      description: 'Get timetable for a level instance',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { levelInstanceId } = request.params as { levelInstanceId: string };
    const timetable = await timetableService.getTimetable(tenantId, levelInstanceId);
    reply.send(timetable);
  });

  fastify.get('/timetable/teacher/me', {
    preHandler: [requireTenant, requireModule('timetable')],
    schema: {
      description: "Get the current teacher's timetable",
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const timetable = await timetableService.getTeacherTimetable(tenantId, request.userId);
    reply.send(timetable);
  });

  fastify.delete('/timetable/:id', {
    preHandler: [requireTenant, requireModule('timetable'), authorize('timetable:*')],
    schema: {
      description: 'Delete a timetable entry',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const { id } = request.params as { id: string };
    await timetableService.deleteEntry(id);
    reply.send({ success: true });
  });
}
