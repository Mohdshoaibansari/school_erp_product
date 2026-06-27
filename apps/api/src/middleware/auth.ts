import { FastifyRequest, FastifyReply } from 'fastify';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_ANON_KEY!
);

declare module 'fastify' {
  interface FastifyRequest {
    userId: string;
  }
}

export async function authMiddleware(request: FastifyRequest, reply: FastifyReply) {
  const authHeader = request.headers.authorization;
  if (!authHeader) {
    reply.status(401).send({ error: 'Missing authorization header' });
    return;
  }

  const token = authHeader.replace('Bearer ', '');
  const { data, error } = await supabase.auth.getUser(token);

  if (error || !data.user) {
    reply.status(401).send({ error: 'Invalid or expired token' });
    return;
  }

  request.userId = data.user.id;
}
