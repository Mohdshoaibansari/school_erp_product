import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { authorize } from '../middleware/authorize';
import { requireTenant } from '../middleware/require-tenant';
import { AttendanceService } from '@school-erp/attendance';
import { AuthorizationService, AcademicService } from '@school-erp/kernel';

const authzService = new AuthorizationService();
const academicService = new AcademicService();
const attendanceService = new AttendanceService(authzService, academicService);

export default async function routes(fastify: FastifyInstance) {
  fastify.post('/attendance/mark', {
    preHandler: [requireTenant, authorize('attendance:mark')],
    schema: {
      description: 'Mark attendance for multiple students',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as {
      records: Array<{ studentId: string; levelInstanceId: string; date: string; status: string }>;
    };
    const records = body.records.map((r) => ({
      studentId: r.studentId,
      levelInstanceId: r.levelInstanceId,
      date: new Date(r.date),
      status: r.status as any,
    }));
    const result = await attendanceService.markAttendance(
      request.userId,
      tenantId,
      records,
    );
    reply.send(result);
  });

  fastify.post('/attendance/mark-all', {
    preHandler: [requireTenant, authorize('attendance:mark')],
    schema: {
      description: 'Mark all given students as present for a level instance and date',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as {
      levelInstanceId: string;
      date: string;
      studentIds: string[];
    };
    const result = await attendanceService.markAllPresent(
      request.userId,
      tenantId,
      body.levelInstanceId,
      new Date(body.date),
      body.studentIds,
    );
    reply.send(result);
  });

  fastify.get('/attendance', {
    preHandler: [requireTenant],
    schema: {
      description: 'Get attendance records by date and level instance',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { date, levelInstanceId } = request.query as { date: string; levelInstanceId: string };
    const records = await attendanceService.getAttendanceByDate(
      levelInstanceId,
      new Date(date),
      tenantId,
    );
    reply.send(records);
  });

  fastify.get('/attendance/report', {
    preHandler: [requireTenant],
    schema: {
      description: 'Get monthly attendance report for a level instance',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { levelInstanceId, startDate, endDate } = request.query as {
      levelInstanceId: string;
      startDate: string;
      endDate: string;
    };
    const report = await attendanceService.getMonthlyReport(
      levelInstanceId,
      new Date(startDate),
      new Date(endDate),
      tenantId,
    );
    reply.send(report);
  });
}
