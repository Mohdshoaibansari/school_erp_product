import { FastifyReply, FastifyRequest } from 'fastify';
import {
  NotFoundError,
  ValidationError,
  StudentLimitExceededError,
  ModuleNotEnabledError,
  UnauthorizedError,
} from '@school-erp/shared';

export function errorHandler(error: Error, request: FastifyRequest, reply: FastifyReply) {
  if (error instanceof NotFoundError) {
    reply.status(404).send({ error: error.message });
    return;
  }
  if (error instanceof ValidationError) {
    reply.status(400).send({ error: error.message });
    return;
  }
  if (error instanceof StudentLimitExceededError) {
    reply.status(402).send({ error: error.message });
    return;
  }
  if (error instanceof ModuleNotEnabledError) {
    reply.status(402).send({ error: error.message });
    return;
  }
  if (error instanceof UnauthorizedError) {
    reply.status(403).send({ error: error.message });
    return;
  }

  console.error(error);
  reply.status(500).send({ error: 'Internal server error' });
}
