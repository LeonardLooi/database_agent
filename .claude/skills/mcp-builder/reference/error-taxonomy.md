# Error Taxonomy for Production MCP Servers

Consistent error handling patterns for MCP servers. For branded types and audit logging, see `error-branded-types-audit.md`.

## 1. Error Taxonomy

### MCPErrorCode Enum

```typescript
export enum MCPErrorCode {
  // Client errors (4xx)
  INVALID_INPUT = 'INVALID_INPUT',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  NOT_FOUND = 'NOT_FOUND',
  RATE_LIMITED = 'RATE_LIMITED',
  VALIDATION_FAILED = 'VALIDATION_FAILED',

  // Server errors (5xx)
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  TIMEOUT = 'TIMEOUT',
  CIRCUIT_OPEN = 'CIRCUIT_OPEN',
  DEPENDENCY_FAILED = 'DEPENDENCY_FAILED',

  // Business logic errors
  BUSINESS_RULE_VIOLATION = 'BUSINESS_RULE_VIOLATION',
  INSUFFICIENT_BALANCE = 'INSUFFICIENT_BALANCE',
  DUPLICATE_OPERATION = 'DUPLICATE_OPERATION',
  OPERATION_NOT_ALLOWED = 'OPERATION_NOT_ALLOWED',
}
```

### MCPError Interface

```typescript
export interface MCPError {
  code: MCPErrorCode;
  message: string;
  details?: Record<string, unknown>;
  retry_after_ms?: number;
  recovery_actions: string[];
  fallback_tool?: string;
  correlation_id: string;
  timestamp: string;
}
```

### MCPErrorFactory Class

```typescript
import { randomUUID } from 'node:crypto';

export class MCPErrorFactory {
  private static readonly RECOVERY_MAP: Record<MCPErrorCode, string[]> = {
    [MCPErrorCode.RATE_LIMITED]: ['wait_and_retry', 'use_cached_data'],
    [MCPErrorCode.CIRCUIT_OPEN]: ['use_fallback_service', 'check_service_status'],
    [MCPErrorCode.TIMEOUT]: ['retry_with_timeout', 'reduce_request_scope'],
    [MCPErrorCode.VALIDATION_FAILED]: ['check_input_format', 'get_schema_info'],
    [MCPErrorCode.NOT_FOUND]: ['verify_resource_id', 'list_available_resources'],
    [MCPErrorCode.UNAUTHORIZED]: ['refresh_token', 'reauthenticate'],
    [MCPErrorCode.FORBIDDEN]: ['check_permissions', 'escalate_to_human'],
    [MCPErrorCode.INVALID_INPUT]: ['check_input_format', 'get_schema_info'],
    [MCPErrorCode.INTERNAL_ERROR]: ['retry_once', 'contact_support'],
    [MCPErrorCode.SERVICE_UNAVAILABLE]: ['wait_and_retry', 'use_fallback'],
    [MCPErrorCode.DEPENDENCY_FAILED]: ['use_fallback_service', 'retry_later'],
    [MCPErrorCode.BUSINESS_RULE_VIOLATION]: ['review_business_rules', 'escalate_to_human'],
    [MCPErrorCode.INSUFFICIENT_BALANCE]: ['check_balance', 'add_funds'],
    [MCPErrorCode.DUPLICATE_OPERATION]: ['get_existing_result', 'skip_operation'],
    [MCPErrorCode.OPERATION_NOT_ALLOWED]: ['check_permissions', 'escalate_to_human'],
  };

  static create(
    code: MCPErrorCode,
    message: string,
    options?: {
      details?: Record<string, unknown>;
      retry_after_ms?: number;
      fallback_tool?: string;
      correlation_id?: string;
    }
  ): MCPError {
    return {
      code,
      message,
      details: options?.details,
      retry_after_ms: options?.retry_after_ms,
      recovery_actions: this.getDefaultRecovery(code),
      fallback_tool: options?.fallback_tool,
      correlation_id: options?.correlation_id ?? randomUUID(),
      timestamp: new Date().toISOString(),
    };
  }

  static getDefaultRecovery(code: MCPErrorCode): string[] {
    return this.RECOVERY_MAP[code] ?? ['contact_support'];
  }
}
```

### Recovery Hints

Recovery hints tell the LLM *how* to recover, not just *what* went wrong:

```typescript
export enum RecoveryHint {
  RETRY_LATER = 'RETRY_LATER',
  CHECK_INPUT = 'CHECK_INPUT',
  TRY_ALTERNATIVE = 'TRY_ALTERNATIVE',
  REPORT_TO_USER = 'REPORT_TO_USER',
}

export interface MCPErrorWithRecovery extends MCPError {
  recovery_hint: RecoveryHint;
  userMessage: string;
}
```

| Hint | When to Use | Agent Behavior |
|------|-------------|----------------|
| `RETRY_LATER` | Rate limits, temporary outages, timeouts | Wait `retry_after_ms`, then retry same call |
| `CHECK_INPUT` | Validation failures, bad formats, missing fields | Fix parameters using `corrective_params`, retry |
| `TRY_ALTERNATIVE` | Feature not available, permission denied for this approach | Use `fallback_tool` or different strategy |
| `REPORT_TO_USER` | Account issues, billing problems, data not found | Surface `userMessage` to the human |

### No-FAKE-EMPTY-Data Principle

Never bridge a technical failure with fake or empty data. The agent must distinguish between "API failed" and "genuinely empty result":

```typescript
// BAD: Silent fallback hides the real error
try {
  return await fetchOrders(userId);
} catch (e) {
  return { orders: [], total: 0 };  // Looks like "no orders" but was actually a failure
}

// GOOD: Errors are errors, empty results are empty results
try {
  const result = await fetchOrders(userId);
  return { orders: result.orders, total: result.total, status: 'success' };
} catch (e) {
  return MCPErrorFactory.create(MCPErrorCode.DEPENDENCY_FAILED, 'Order service unavailable', {
    recovery_hint: RecoveryHint.RETRY_LATER,
    userMessage: 'Could not load orders. The order service is temporarily unavailable.',
    retry_after_ms: 5000,
  });
}
```

**Rule:** If a tool handler catches an exception, it MUST return an error response — never an empty-but-successful-looking result.

### Usage Example

```typescript
import { MCPErrorFactory, MCPErrorCode, MCPError } from './errors.js';

async function handleGetOrder(orderId: string): Promise<{ content: Array<{ type: string; text: string }> } | { isError: true; content: Array<{ type: string; text: string }> }> {
  try {
    const order = await orderService.getById(orderId);

    if (!order) {
      const error = MCPErrorFactory.create(MCPErrorCode.NOT_FOUND, `Order ${orderId} not found`, {
        details: { orderId },
        fallback_tool: 'list_orders',
      });
      return { isError: true, content: [{ type: 'text', text: JSON.stringify(error, null, 2) }] };
    }

    return { content: [{ type: 'text', text: JSON.stringify(order, null, 2) }] };
  } catch (err) {
    const error = MCPErrorFactory.create(MCPErrorCode.INTERNAL_ERROR, 'Failed to retrieve order', {
      details: { orderId, originalError: err instanceof Error ? err.message : String(err) },
    });
    return { isError: true, content: [{ type: 'text', text: JSON.stringify(error, null, 2) }] };
  }
}
```
