import { FastifyRequest, FastifyReply } from 'fastify';
import { AuthorizationService } from '@school-erp/kernel';

const authzService = new AuthorizationService();

export function authorize(permission: string) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    if (!request.tenantId) {
      reply.status(400).send({ error: 'Missing tenant' });
      return;
    }
    try {
      await authzService.enforcePermission(request.userId, request.tenantId, permission);
    } catch {
      reply.status(403).send({ error: 'Forbidden' });
    }
  };
}
