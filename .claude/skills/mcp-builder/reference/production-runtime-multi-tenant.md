# Production Runtime — Multi-Tenant Support

AsyncLocalStorage-based tenant context, quota enforcement, and audit logging for SaaS MCP servers. For graceful shutdown and health checks, see `production-runtime-shutdown-health.md`.

## 1. Tenant Context Types

```typescript
// src/multi-tenant/types.ts
export interface TenantContext {
  tenantId: string;
  organizationId: string;
  userId: string;
  permissions: string[];
  quotas: TenantQuotas;
}

export interface TenantQuotas {
  maxRequestsPerMinute: number;
  maxToolCallsPerHour: number;
  maxDataExportMb: number;
}

export class TenantContextNotFoundError extends Error {
  constructor() {
    super('Tenant context not found. Ensure request is within tenant scope.');
    this.name = 'TenantContextNotFoundError';
  }
}
```

## 2. AsyncLocalStorage Context

```typescript
// src/multi-tenant/context.ts
import { AsyncLocalStorage } from 'node:async_hooks';
import { TenantContext, TenantContextNotFoundError } from './types.js';

const asyncLocalStorage = new AsyncLocalStorage<TenantContext>();

export function withTenantContext<T>(
  context: TenantContext,
  fn: () => T | Promise<T>
): T | Promise<T> {
  return asyncLocalStorage.run(context, fn);
}

export function getTenantContext(): TenantContext | undefined {
  return asyncLocalStorage.getStore();
}

export function requireTenantContext(): TenantContext {
  const context = getTenantContext();
  if (!context) {
    throw new TenantContextNotFoundError();
  }
  return context;
}
```

## 3. Tenant Middleware

```typescript
// src/multi-tenant/middleware.ts
import { FastifyRequest, FastifyReply } from 'fastify';
import { withTenantContext } from './context.js';
import { TenantContext } from './types.js';
import { loadTenantFromDatabase } from './loader.js';

export async function tenantMiddleware(
  request: FastifyRequest,
  reply: FastifyReply
): Promise<void> {
  const tenantId = request.headers['x-tenant-id'] as string;
  const userId = request.headers['x-user-id'] as string;

  if (!tenantId || !userId) {
    return reply.status(400).send({
      error: 'Missing required headers: x-tenant-id, x-user-id',
    });
  }

  try {
    const tenantData = await loadTenantFromDatabase(tenantId, userId);

    const context: TenantContext = {
      tenantId,
      organizationId: tenantData.organizationId,
      userId,
      permissions: tenantData.permissions,
      quotas: tenantData.quotas,
    };

    await withTenantContext(context, async () => {
      return;
    });
  } catch (error) {
    return reply.status(403).send({ error: 'Invalid tenant or user' });
  }
}
```

## 4. Quota Enforcement

```typescript
// src/multi-tenant/quota-enforcer.ts
import { requireTenantContext } from './context.js';
import { RedisClientType } from 'redis';

export class QuotaEnforcer {
  constructor(private redis: RedisClientType) {}

  async checkRequestQuota(): Promise<boolean> {
    const context = requireTenantContext();
    const key = `quota:requests:${context.tenantId}`;
    const count = await this.redis.incr(key);

    if (count === 1) {
      await this.redis.expire(key, 60); // 1 minute window
    }

    return count <= context.quotas.maxRequestsPerMinute;
  }

  async checkToolCallQuota(): Promise<boolean> {
    const context = requireTenantContext();
    const key = `quota:tools:${context.tenantId}`;
    const count = await this.redis.incr(key);

    if (count === 1) {
      await this.redis.expire(key, 3600); // 1 hour window
    }

    return count <= context.quotas.maxToolCallsPerHour;
  }
}
```

## 5. Tenant-Scoped Audit Logger

```typescript
// src/multi-tenant/audit-logger.ts
import { requireTenantContext } from './context.js';

export interface AuditLog {
  tenant_id: string;
  user_id: string;
  action: string;
  resource: string;
  metadata: Record<string, unknown>;
  timestamp: Date;
}

export class AuditLogger {
  async log(action: string, resource: string, metadata: Record<string, unknown> = {}): Promise<void> {
    const context = requireTenantContext();

    const auditLog: AuditLog = {
      tenant_id: context.tenantId,
      user_id: context.userId,
      action,
      resource,
      metadata,
      timestamp: new Date(),
    };

    console.log('AUDIT:', JSON.stringify(auditLog));
    // In production, persist to database or audit service
  }
}
```

## 6. Tool Execution with Tenant Isolation

```typescript
// src/protocol/tool-execution.ts
import { requireTenantContext } from '../multi-tenant/context.js';
import { QuotaEnforcer } from '../multi-tenant/quota-enforcer.js';
import { AuditLogger } from '../multi-tenant/audit-logger.js';

export async function executeTool(
  toolName: string,
  args: Record<string, unknown>,
  quotaEnforcer: QuotaEnforcer,
  auditLogger: AuditLogger
): Promise<unknown> {
  const context = requireTenantContext();

  const allowed = await quotaEnforcer.checkToolCallQuota();
  if (!allowed) {
    throw new Error(`Tool call quota exceeded for tenant ${context.tenantId}`);
  }

  await auditLogger.log('tool_call', toolName, { args });

  // Tool implementation should use requireTenantContext() to scope data access
  const result = await executeToolImplementation(toolName, args);
  return result;
}

async function executeToolImplementation(
  toolName: string,
  args: Record<string, unknown>
): Promise<unknown> {
  return { success: true };
}
```

## Usage Notes

1. **Multi-Tenancy**: AsyncLocalStorage propagates context through async call chains without explicit passing
2. **Quota Enforcement**: Redis-backed sliding windows for per-tenant rate limiting
3. **Audit Logging**: Every tool call logged with tenant context for compliance
4. **Data Isolation**: All tool implementations should call `requireTenantContext()` to scope queries
