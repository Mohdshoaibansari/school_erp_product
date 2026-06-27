import Fastify from 'fastify';
import cors from '@fastify/cors';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import { errorHandler } from './middleware/error-handler';
import { tenantMiddleware } from './middleware/tenant';
import { authMiddleware } from './middleware/auth';
import studentRoutes from './routes/students';
import attendanceRoutes from './routes/attendance';
import feeRoutes from './routes/fees';
import timetableRoutes from './routes/timetable';
import examRoutes from './routes/exams';
import adminRoutes from './routes/admin';

export async function buildApp() {
  const app = Fastify({ logger: true });

  await app.register(cors);

  await app.register(swagger, {
    openapi: {
      info: {
        title: 'School ERP API',
        version: '1.0.0',
        description: 'Multi-tenant School ERP REST API',
      },
    },
  });

  await app.register(swaggerUi, {
    routePrefix: '/docs',
  });

  app.setErrorHandler(errorHandler);

  app.addHook('onRequest', tenantMiddleware);
  app.addHook('onRequest', authMiddleware);

  app.get('/health', async () => ({ status: 'ok' }));

  await app.register(adminRoutes, { prefix: '/api' });
  await app.register(studentRoutes, { prefix: '/api' });
  await app.register(attendanceRoutes, { prefix: '/api' });
  await app.register(feeRoutes, { prefix: '/api' });
  await app.register(timetableRoutes, { prefix: '/api' });
  await app.register(examRoutes, { prefix: '/api' });

  return app;
}

export async function start() {
  const app = await buildApp();
  const port = Number(process.env.API_PORT) || 3000;
  const host = process.env.API_HOST || '0.0.0.0';

  await app.listen({ port, host });
  console.log(`Server running at http://${host}:${port}`);
  console.log(`API docs at http://${host}:${port}/docs`);
  return app;
}

start().catch(console.error);
