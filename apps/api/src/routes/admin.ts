import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { authorize } from '../middleware/authorize';
import { requireTenant } from '../middleware/require-tenant';
import { TenantService, IdentityService, SubscriptionService } from '@school-erp/kernel';
import type { ModuleName } from '@school-erp/shared';

const tenantService = new TenantService();
const identityService = new IdentityService();
const subscriptionService = new SubscriptionService();

export default async function routes(fastify: FastifyInstance) {
  fastify.post('/admin/signup', {
    schema: {
      description: 'Create a new school tenant and first admin user',
      response: {
        201: {
          type: 'object',
          properties: {
            tenantId: { type: 'string' },
            userId: { type: 'string' },
          },
        },
      },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const body = request.body as {
      schoolName: string;
      subdomain: string;
      adminEmail: string;
      adminName: string;
      adminPhone?: string;
      supabaseId: string;
    };

    const tenant = await tenantService.create({
      name: body.schoolName,
      subdomain: body.subdomain,
      adminEmail: body.adminEmail,
      adminName: body.adminName,
      adminPhone: body.adminPhone,
    });

    await subscriptionService.setupFreeTier(tenant.id);

    const { user } = await identityService.createUser({
      tenantId: tenant.id,
      email: body.adminEmail,
      name: body.adminName,
      phone: body.adminPhone,
      role: 'SCHOOL_ADMIN',
      supabaseId: body.supabaseId,
    });

    reply.status(201).send({ tenantId: tenant.id, userId: user.id });
  });

  fastify.get('/admin/tenant', {
    preHandler: [requireTenant, authorize('*')],
    schema: {
      description: 'Get current tenant configuration',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const tenant = await tenantService.getById(tenantId);
    reply.send(tenant);
  });

  fastify.patch('/admin/tenant/status', {
    preHandler: [requireTenant, authorize('*')],
    schema: {
      description: 'Update tenant status',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { status } = request.body as { status: string };
    const tenant = await tenantService.updateStatus(tenantId, status as any);
    reply.send(tenant);
  });

  fastify.patch('/admin/tenant/student-limit', {
    preHandler: [requireTenant, authorize('*')],
    schema: {
      description: 'Update tenant student limit',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { limit } = request.body as { limit: number };
    const tenant = await tenantService.updateStudentLimit(tenantId, limit);
    reply.send(tenant);
  });

  fastify.get('/admin/tenant/student-count', {
    preHandler: [requireTenant, authorize('*')],
    schema: {
      description: 'Get current active student count for the tenant',
      response: { 200: { type: 'number' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const count = await tenantService.getStudentCount(tenantId);
    reply.send(count);
  });

  fastify.get('/admin/modules', {
    preHandler: [requireTenant, authorize('*')],
    schema: {
      description: 'Get enabled modules for the tenant',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const modules = await subscriptionService.getEnabledModules(tenantId);
    reply.send(modules);
  });

  fastify.post('/admin/modules', {
    preHandler: [requireTenant, authorize('*')],
    schema: {
      description: 'Enable or disable a module for the tenant',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const body = request.body as { moduleName: ModuleName; action: 'enable' | 'disable' };

    if (body.action === 'enable') {
      const result = await subscriptionService.enableModule(tenantId, body.moduleName);
      reply.send(result);
    } else {
      const result = await subscriptionService.disableModule(tenantId, body.moduleName);
      reply.send(result);
    }
  });

  fastify.get('/admin/student-limit', {
    preHandler: [requireTenant, authorize('*')],
    schema: {
      description: 'Get student limit status for the tenant',
      response: {
        200: {
          type: 'object',
          properties: {
            current: { type: 'number' },
            limit: { type: 'number' },
            isAtLimit: { type: 'boolean' },
          },
        },
      },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const status = await subscriptionService.getStudentLimitStatus(tenantId);
    reply.send(status);
  });

  fastify.get('/admin/users', {
    preHandler: [requireTenant, authorize('*')],
    schema: {
      description: 'List users in the tenant',
      response: { 200: { type: 'array', items: { type: 'object' } } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const tenantId = request.tenantId!;
    const { skip, take } = request.query as { skip?: string; take?: string };
    const users = await identityService.getUsersByTenant(
      tenantId,
      skip ? parseInt(skip) : 0,
      take ? parseInt(take) : 50,
    );
    reply.send(users);
  });

  fastify.patch('/admin/users/:id/suspend', {
    preHandler: [requireTenant, authorize('*')],
    schema: {
      description: 'Suspend a user',
      response: { 200: { type: 'object' } },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    const { id } = request.params as { id: string };
    const user = await identityService.suspendUser(id);
    reply.send(user);
  });
}
