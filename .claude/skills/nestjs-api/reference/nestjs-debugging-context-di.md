# NestJS Debugging — Context, DI & Configuration

AsyncLocalStorage context debugging, dependency injection troubleshooting, environment configuration, and a quick-reference troubleshooting table for NestJS 11.x with Fastify and Prisma ORM.

## 4. AsyncLocalStorage & Request Context Debugging

### Common Context Loss Issues

```typescript
// src/common/context/request-context.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { AsyncLocalStorage } from 'async_hooks';

interface RequestContext {
  correlationId: string;
  userId?: string;
  timestamp: number;
}

@Injectable()
export class RequestContextService {
  private readonly als = new AsyncLocalStorage<RequestContext>();
  private readonly logger = new Logger(RequestContextService.name);

  run<T>(context: RequestContext, callback: () => T): T {
    this.logger.debug(`Creating context: ${JSON.stringify(context)}`, 'ALS');
    return this.als.run(context, callback);
  }

  get(): RequestContext | undefined {
    const context = this.als.getStore();
    if (!context) {
      this.logger.warn('Context not found in current async scope', 'ALS');
    }
    return context;
  }

  // Pattern: wrap async operations to preserve context
  wrapAsync<T>(fn: () => Promise<T>): Promise<T> {
    const context = this.get();
    if (!context) {
      this.logger.error('Cannot wrap async operation: no active context', 'ALS');
      throw new Error('No active request context');
    }

    return this.als.run(context, async () => {
      this.logger.debug(`Wrapped async operation with context: ${context.correlationId}`, 'ALS');
      return fn();
    });
  }

  // Fix for setTimeout/setInterval context loss
  wrapTimeout(callback: () => void, delay: number): NodeJS.Timeout {
    const context = this.get();
    if (!context) {
      this.logger.warn('setTimeout called without context', 'ALS');
      return setTimeout(callback, delay);
    }

    return setTimeout(() => {
      this.als.run(context, callback);
    }, delay);
  }
}
```

### Debugging Context in Prisma Middleware

```typescript
// src/database/prisma.service.ts (additional middleware)
async onModuleInit() {
  await this.$connect();

  // Prisma middleware to propagate context
  this.$use(async (params, next) => {
    const context = this.contextService.get();
    if (!context) {
      this.logger.warn(`Prisma query without context: ${params.model}.${params.action}`, 'PrismaContext');
    } else {
      this.logger.debug(
        `Prisma query with context ${context.correlationId}: ${params.model}.${params.action}`,
        'PrismaContext'
      );
    }
    return next(params);
  });
}
```

### Context Loss in Bull Queue Jobs

```typescript
// src/queues/email.processor.ts
import { Processor, Process } from '@nestjs/bull';
import { Job } from 'bull';
import { Logger } from '@nestjs/common';
import { RequestContextService } from '../common/context/request-context.service';

@Processor('email')
export class EmailProcessor {
  private readonly logger = new Logger(EmailProcessor.name);

  constructor(private readonly contextService: RequestContextService) {}

  @Process('send')
  async handleSend(job: Job) {
    // Context is NOT automatically propagated to queue jobs
    // Solution: store context in job.data and recreate it
    const { correlationId, userId, ...emailData } = job.data;

    return this.contextService.run(
      { correlationId, userId, timestamp: Date.now() },
      async () => {
        this.logger.log(`Processing email job with context: ${correlationId}`, 'EmailProcessor');
        // Now all async operations in this scope have context
        return this.sendEmail(emailData);
      }
    );
  }

  private async sendEmail(data: any) {
    const context = this.contextService.get();
    this.logger.debug(`Sending email in context: ${context?.correlationId || 'MISSING'}`, 'EmailProcessor');
    // ... send email
  }
}
```

## 5. Dependency Injection Debugging

### Common DI Issues and Fixes

```typescript
// Issue: "Cannot resolve dependency" error
// Symptom: Nest can't find a provider

// BAD: Service not in module providers
@Module({
  controllers: [UsersController],
  // Missing: UsersService in providers array
})
export class UsersModule {}

// GOOD: Service registered in module
@Module({
  controllers: [UsersController],
  providers: [UsersService],
  exports: [UsersService], // Export if other modules need it
})
export class UsersModule {}

// Issue: Circular dependency
// Symptom: "A circular dependency has been detected"

// BAD: Direct circular reference
@Injectable()
export class UserService {
  constructor(private readonly postService: PostService) {}
}

@Injectable()
export class PostService {
  constructor(private readonly userService: UserService) {} // Circular!
}

// GOOD: Use forwardRef
@Injectable()
export class UserService {
  constructor(@Inject(forwardRef(() => PostService)) private readonly postService: PostService) {}
}

@Injectable()
export class PostService {
  constructor(@Inject(forwardRef(() => UserService)) private readonly userService: UserService) {}
}

// Issue: Optional dependency
// Symptom: App crashes when optional service is missing

// BAD: Required dependency that might not exist
@Injectable()
export class NotificationService {
  constructor(private readonly smsProvider: SmsProvider) {} // Crashes if SMS not configured
}

// GOOD: Use @Optional() decorator
@Injectable()
export class NotificationService {
  constructor(@Optional() private readonly smsProvider?: SmsProvider) {}

  async send(message: string) {
    if (this.smsProvider) {
      await this.smsProvider.send(message);
    } else {
      console.log('SMS provider not configured, skipping SMS notification');
    }
  }
}

// Issue: Module import ordering
// Symptom: Provider from Module A not available in Module B

// BAD: Importing module that doesn't export the provider
@Module({
  imports: [DatabaseModule], // DatabaseModule doesn't export PrismaService
  providers: [UserService], // UserService needs PrismaService - ERROR!
})
export class UserModule {}

// GOOD: Ensure DatabaseModule exports PrismaService
@Module({
  providers: [PrismaService],
  exports: [PrismaService], // Now available to importing modules
})
export class DatabaseModule {}
```

## 6. Environment & Configuration Debugging

### Fail-Fast Static Configuration

```typescript
// src/config/static-config.ts
import { Logger } from '@nestjs/common';
import * as dotenv from 'dotenv';

dotenv.config();

const logger = new Logger('StaticConfig');

function getEnv(key: string, defaultValue?: string): string {
  const value = process.env[key];
  if (!value && defaultValue === undefined) {
    logger.error(`Missing required environment variable: ${key}`);
    throw new Error(`Missing required environment variable: ${key}`);
  }
  const result = value || defaultValue!;
  logger.debug(`Loaded ${key}=${result.includes('PASSWORD') ? '***' : result}`);
  return result;
}

export const Config = {
  nodeEnv: getEnv('NODE_ENV', 'development'),
  port: parseInt(getEnv('PORT', '3000'), 10),
  databaseUrl: getEnv('DATABASE_URL'),
  jwtSecret: getEnv('JWT_SECRET'),
  isDevelopment: getEnv('NODE_ENV', 'development') === 'development',
  isProduction: getEnv('NODE_ENV') === 'production',
} as const;

logger.log(`Configuration loaded for environment: ${Config.nodeEnv}`);
```

### Debugging .env File Loading

```bash
# Check if .env file is loaded
node -e "require('dotenv').config(); console.log(process.env)"

# Check specific variable
node -e "require('dotenv').config(); console.log('DATABASE_URL:', process.env.DATABASE_URL)"

# Environment variable precedence (highest to lowest):
# 1. System environment variables (export VAR=value)
# 2. .env.local (not committed to git)
# 3. .env
# 4. Default values in code

# Debug: print all process.env at startup
# src/main.ts
if (Config.isDevelopment) {
  console.log('Environment variables:', JSON.stringify(process.env, null, 2));
}
```

## 7. Troubleshooting Table

| Issue | Symptom | Fix |
|-------|---------|-----|
| Route not found | 404 for valid endpoint | Check controller path prefix, ensure module is imported in AppModule |
| Request body is undefined | `req.body` is `{}` | Register `@nestjs/platform-fastify` body parser, ensure `Content-Type: application/json` |
| Validation not working | Invalid data passes through | Apply `ValidationPipe` globally in `main.ts`, ensure DTO has `class-validator` decorators |
| Circular dependency | Module initialization fails | Use `forwardRef(() => Module)` in imports and `@Inject(forwardRef(() => Service))` in constructor |
| Prisma "Connection pool timeout" | Queries hang indefinitely | Increase `connection_limit` in `DATABASE_URL`, check for unclosed transactions, ensure `$disconnect()` in tests |
| Context lost in async operations | `contextService.get()` returns `undefined` | Use `contextService.wrapAsync()` or manually propagate context with `als.run()` |
| Config value is undefined | `Config.someValue` is `undefined` | Check `.env` file exists, variable name matches, dotenv loaded before config import |
| Fastify validation error | `FST_ERR_VALIDATION` in logs | Check route schema matches DTO, ensure JSON schema plugin installed, validate request body manually |
| Middleware not executing | Custom middleware skipped | Ensure middleware applied globally or to specific routes, check execution order |
| JWT authentication fails | 401 Unauthorized for valid token | Check JWT secret matches, verify token not expired, ensure AuthGuard applied correctly |
| Prisma migration fails | `Migration failed` error | Check schema syntax, ensure database accessible, rollback failed migration, check for conflicting migrations |
| Bull queue job fails silently | Job completes but no effect | Check processor decorated with `@Processor()`, ensure queue registered in module, add error logging in `@OnQueueFailed()` |
