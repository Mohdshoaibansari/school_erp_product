import { FastifyRequest, FastifyReply } from 'fastify';
import { TenantService } from '@school-erp/kernel';

const tenantService = new TenantService();

declare module 'fastify' {
  interface FastifyRequest {
    tenantId?: string;
  }
}

export async function tenantMiddleware(request: FastifyRequest, reply: FastifyReply) {
  const host = (request.headers.host ?? '').split(':')[0];
  const parts = host.split('.');

  if (parts.length <= 1 || host === 'localhost' || host.startsWith('127.')) {
    return;
  }

  const subdomain = parts[0];

  try {
    const tenant = await tenantService.getBySubdomain(subdomain);
    request.tenantId = tenant.id;
  } catch {
    request.tenantId = undefined;
  }
}
