import { FastifyRequest, FastifyReply } from 'fastify';

export async function requireTenant(request: FastifyRequest, reply: FastifyReply) {
  if (!request.tenantId) {
    reply.status(400).send({ error: 'Tenant not resolved. Access via your school subdomain.' });
  }
}
