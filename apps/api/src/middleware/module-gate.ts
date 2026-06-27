import { FastifyRequest, FastifyReply } from 'fastify';
import { SubscriptionService } from '@school-erp/kernel';
import { ModuleName } from '@school-erp/shared';

const subscriptionService = new SubscriptionService();

export function requireModule(moduleName: ModuleName) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    if (!request.tenantId) {
      reply.status(400).send({ error: 'Missing tenant' });
      return;
    }
    try {
      await subscriptionService.enforceModuleEnabled(request.tenantId, moduleName);
    } catch {
      reply.status(402).send({ error: `The ${moduleName} module is not enabled for this school.` });
    }
  };
}
