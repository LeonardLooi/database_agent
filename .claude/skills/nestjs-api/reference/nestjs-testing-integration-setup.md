# NestJS 11.x Integration Testing — Setup & Testcontainers

Integration test configuration, full app bootstrapping with supertest and Fastify, and Testcontainers PostgreSQL setup for NestJS 11.x.

## Vitest Configuration for Integration Tests

### vitest.e2e.config.ts

```typescript
import { defineConfig } from 'vitest/config';
import swc from 'unplugin-swc';
import { resolve } from 'path';

export default defineConfig({
  test: {
    globals: true,
    root: './',
    environment: 'node',
    include: ['**/*.e2e-spec.ts'],
    testTimeout: 60000,
    hookTimeout: 60000,
    poolOptions: {
      threads: {
        singleThread: true,
      },
    },
  },
  plugins: [
    swc.vite({
      module: { type: 'es6' },
      jsc: {
        parser: {
          syntax: 'typescript',
          decorators: true,
        },
        transform: {
          decoratorMetadata: true,
        },
        target: 'es2022',
      },
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
});
```

## Full App Bootstrap with supertest

```typescript
// test/users.e2e-spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import {
  FastifyAdapter,
  NestFastifyApplication,
} from '@nestjs/platform-fastify';
import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import request from 'supertest';
import { AppModule } from '@/app.module';
import { ValidationPipe } from '@nestjs/common';
import { DatabaseService } from '@/core/database/database.service';
import { GenericContainer, StartedTestContainer } from 'testcontainers';

describe('Users API (e2e)', () => {
  let app: NestFastifyApplication;
  let databaseService: DatabaseService;
  let postgresContainer: StartedTestContainer;

  beforeAll(async () => {
    // Start PostgreSQL container
    postgresContainer = await new GenericContainer('postgres:16-alpine')
      .withEnvironment({
        POSTGRES_USER: 'test',
        POSTGRES_PASSWORD: 'test',
        POSTGRES_DB: 'testdb',
      })
      .withExposedPorts(5432)
      .start();

    const port = postgresContainer.getMappedPort(5432);
    const databaseUrl = `postgresql://test:test@localhost:${port}/testdb`;

    // Set environment variable for Prisma
    process.env.DATABASE_URL = databaseUrl;

    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication<NestFastifyApplication>(
      new FastifyAdapter(),
    );

    app.useGlobalPipes(
      new ValidationPipe({
        whitelist: true,
        forbidNonWhitelisted: true,
        transform: true,
      }),
    );

    databaseService = app.get<DatabaseService>(DatabaseService);

    // Run migrations
    const { execSync } = await import('child_process');
    execSync('npx prisma migrate deploy', {
      env: { ...process.env, DATABASE_URL: databaseUrl },
    });

    await app.init();
    await app.getHttpAdapter().getInstance().ready();
  });

  afterAll(async () => {
    await databaseService.$disconnect();
    await app.close();
    await postgresContainer.stop();
  });

  beforeEach(async () => {
    // Clean database before each test
    await databaseService.user.deleteMany();
  });

  describe('/api/v1/users (POST)', () => {
    it('should create a new user', async () => {
      const createUserDto = {
        email: 'test@example.com',
        name: 'Test User',
        role: 'USER',
      };

      const response = await request(app.getHttpServer())
        .post('/api/v1/users')
        .send(createUserDto)
        .expect(201);

      expect(response.body).toMatchObject({
        email: createUserDto.email,
        name: createUserDto.name,
        role: createUserDto.role,
        isActive: true,
      });
      expect(response.body.id).toBeDefined();
      expect(response.body.createdAt).toBeDefined();

      // Verify in database
      const user = await databaseService.user.findUnique({
        where: { id: response.body.id },
      });
      expect(user).not.toBeNull();
      expect(user?.email).toBe(createUserDto.email);
    });

    it('should return 400 for invalid email', async () => {
      const invalidDto = {
        email: 'invalid-email',
        name: 'Test User',
        role: 'USER',
      };

      const response = await request(app.getHttpServer())
        .post('/api/v1/users')
        .send(invalidDto)
        .expect(400);

      expect(response.body.message).toContain('email');
    });

    it('should return 409 for duplicate email', async () => {
      const createUserDto = {
        email: 'duplicate@example.com',
        name: 'Test User',
        role: 'USER',
      };

      // Create first user
      await request(app.getHttpServer())
        .post('/api/v1/users')
        .send(createUserDto)
        .expect(201);

      // Try to create duplicate
      await request(app.getHttpServer())
        .post('/api/v1/users')
        .send(createUserDto)
        .expect(409);
    });
  });

  describe('/api/v1/users (GET)', () => {
    it('should return paginated users', async () => {
      // Create test users
      await databaseService.user.createMany({
        data: [
          { email: 'user1@example.com', name: 'User 1', role: 'USER' },
          { email: 'user2@example.com', name: 'User 2', role: 'ADMIN' },
        ],
      });

      const response = await request(app.getHttpServer())
        .get('/api/v1/users')
        .query({ page: 1, limit: 10 })
        .expect(200);

      expect(response.body.data).toHaveLength(2);
      expect(response.body.meta).toMatchObject({
        total: 2,
        page: 1,
        limit: 10,
        totalPages: 1,
      });
    });
  });

  describe('CRUD Flow', () => {
    it('should complete full CRUD lifecycle', async () => {
      // CREATE
      const createResponse = await request(app.getHttpServer())
        .post('/api/v1/users')
        .send({
          email: 'crud@example.com',
          name: 'CRUD User',
          role: 'USER',
        })
        .expect(201);

      const userId = createResponse.body.id;

      // READ
      const getResponse = await request(app.getHttpServer())
        .get(`/api/v1/users/${userId}`)
        .expect(200);

      expect(getResponse.body.email).toBe('crud@example.com');

      // UPDATE
      const updateResponse = await request(app.getHttpServer())
        .patch(`/api/v1/users/${userId}`)
        .send({ name: 'Updated CRUD User' })
        .expect(200);

      expect(updateResponse.body.name).toBe('Updated CRUD User');

      // Verify update in database
      const updatedUser = await databaseService.user.findUnique({
        where: { id: userId },
      });
      expect(updatedUser?.name).toBe('Updated CRUD User');

      // DELETE
      await request(app.getHttpServer())
        .delete(`/api/v1/users/${userId}`)
        .expect(200);

      // Verify soft delete
      const deletedUser = await databaseService.user.findUnique({
        where: { id: userId },
      });
      expect(deletedUser?.isActive).toBe(false);
    });
  });
});
```

## Testcontainers — Real PostgreSQL

```typescript
// test/helpers/testcontainers.ts
import { GenericContainer, StartedTestContainer } from 'testcontainers';

export class PostgresTestContainer {
  private container: StartedTestContainer | null = null;

  async start(): Promise<string> {
    this.container = await new GenericContainer('postgres:16-alpine')
      .withEnvironment({
        POSTGRES_USER: 'test',
        POSTGRES_PASSWORD: 'test',
        POSTGRES_DB: 'testdb',
      })
      .withExposedPorts(5432)
      .withStartupTimeout(120000)
      .start();

    const host = this.container.getHost();
    const port = this.container.getMappedPort(5432);

    return `postgresql://test:test@${host}:${port}/testdb`;
  }

  async stop(): Promise<void> {
    if (this.container) {
      await this.container.stop();
    }
  }

  async reset(databaseUrl: string): Promise<void> {
    const { PrismaClient } = await import('@prisma/client');
    const prisma = new PrismaClient({
      datasources: {
        db: {
          url: databaseUrl,
        },
      },
    });

    // Get all table names
    const tables = await prisma.$queryRaw<Array<{ tablename: string }>>`
      SELECT tablename FROM pg_tables WHERE schemaname='public'
    `;

    // Truncate all tables
    for (const { tablename } of tables) {
      if (tablename !== '_prisma_migrations') {
        await prisma.$executeRawUnsafe(
          `TRUNCATE TABLE "${tablename}" CASCADE`,
        );
      }
    }

    await prisma.$disconnect();
  }
}

// Usage in test setup
import { PostgresTestContainer } from './helpers/testcontainers';

describe('Integration Tests', () => {
  const postgres = new PostgresTestContainer();
  let databaseUrl: string;

  beforeAll(async () => {
    databaseUrl = await postgres.start();
    process.env.DATABASE_URL = databaseUrl;

    // Run migrations
    const { execSync } = await import('child_process');
    execSync('npx prisma migrate deploy', {
      env: { ...process.env, DATABASE_URL: databaseUrl },
    });
  });

  afterAll(async () => {
    await postgres.stop();
  });

  beforeEach(async () => {
    await postgres.reset(databaseUrl);
  });
});
```
