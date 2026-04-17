## Connection Pool

### Undici Pool Manager Configuration

```typescript
import { Pool } from 'undici';

interface PoolConfig {
  connections: number;           // Max connections per origin
  pipelining: number;            // Max pipelined requests
  connectTimeout: number;        // Connection timeout in ms
  bodyTimeout: number;           // Body timeout in ms
  headersTimeout: number;        // Headers timeout in ms
  keepAliveTimeout: number;      // Keep-alive timeout in ms
  keepAliveMaxTimeout: number;   // Max keep-alive timeout in ms
}

export function createConnectionPool(url: string, config: PoolConfig): Pool {
  return new Pool(url, {
    connections: config.connections,
    pipelining: config.pipelining,
    connectTimeout: config.connectTimeout,
    bodyTimeout: config.bodyTimeout,
    headersTimeout: config.headersTimeout,
    keepAliveTimeout: config.keepAliveTimeout,
    keepAliveMaxTimeout: config.keepAliveMaxTimeout,
  });
}
```

## Production Configuration

### Complete Resilience Stack

```typescript
export const PRODUCTION_RESILIENCE_CONFIG = {
  // Connection Pool
  pool: {
    connections: 10,
    pipelining: 1,
    connectTimeout: 10_000,
    bodyTimeout: 30_000,
    headersTimeout: 10_000,
    keepAliveTimeout: 4_000,
    keepAliveMaxTimeout: 600_000,
  },

  // Circuit Breaker
  circuitBreaker: {
    failureThreshold: 5,
    successThreshold: 2,
    timeout: 60_000,              // 1 minute before half-open
    monitoringPeriod: 120_000,    // 2 minute rolling window
  },

  // Bulkhead
  bulkhead: {
    maxConcurrent: 10,
    maxQueue: 20,
    queueTimeout: 5_000,
  },

  // Rate Limiter
  rateLimiter: {
    maxRequests: 50,
    windowMs: 60_000,             // 50 requests per minute
    burstSize: 60,
  },

  // Retry Strategy
  retry: {
    maxAttempts: 3,
    initialDelay: 100,
    maxDelay: 5_000,
    backoffMultiplier: 2,
    jitterFactor: 0.1,
    retryableErrors: [
      // ── Network errors (transient, safe to retry) ──────────────────────────
      'ECONNRESET',
      'ETIMEDOUT',
      'ENOTFOUND',
      'ECONNREFUSED',
      'EAI_AGAIN',
      'socket hang up',
      // ── HTTP 429 (rate limited — retry after backoff) ──────────────────────
      '429',
      // ── HTTP 5xx (server-side transient failures) ─────────────────────────
      '500',
      '502',
      '503',
      '504',
      // ── NEVER add 4xx here ────────────────────────────────────────────────
      // 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found,
      // 422 Unprocessable Entity — all mean the REQUEST is wrong.
      // Retrying a bad request wastes quota and will always fail.
      // 4xx = caller bug; 5xx = server bug.
    ],
  },
} as const;
```

### Composing Resilience Patterns

```typescript
import { Pool } from 'undici';

export class ResilientHttpClient {
  private pool: Pool;
  private circuitBreaker: CircuitBreaker;
  private bulkhead: Bulkhead;
  private rateLimiter: RateLimiter;
  private retry: RetryStrategy;

  constructor(baseUrl: string, config = PRODUCTION_RESILIENCE_CONFIG) {
    this.pool = createConnectionPool(baseUrl, config.pool);
    this.circuitBreaker = new CircuitBreaker(config.circuitBreaker);
    this.bulkhead = new Bulkhead(config.bulkhead);
    this.rateLimiter = new RateLimiter(config.rateLimiter);
    this.retry = new RetryStrategy(config.retry);
  }

  async request<T>(path: string, options?: any): Promise<T> {
    return this.rateLimiter.execute(() =>
      this.bulkhead.execute(() =>
        this.circuitBreaker.execute(() =>
          this.retry.execute(async () => {
            const response = await this.pool.request({
              path,
              method: options?.method || 'GET',
              headers: options?.headers,
              body: options?.body,
            });

            if (response.statusCode >= 400) {
              throw new Error(`HTTP ${response.statusCode}: ${response.statusMessage}`);
            }

            return response.body.json() as Promise<T>;
          })
        )
      )
    );
  }

  getMetrics() {
    return {
      circuitBreaker: this.circuitBreaker.getMetrics(),
      bulkhead: this.bulkhead.getMetrics(),
      rateLimiter: this.rateLimiter.getMetrics(),
    };
  }

  async close(): Promise<void> {
    await this.pool.close();
  }
}
```

### Usage Example

```typescript
const client = new ResilientHttpClient('https://api.example.com');

try {
  const data = await client.request<UserData>('/users/123');
  console.log('User data:', data);
} catch (error) {
  console.error('Request failed after all resilience attempts:', error);
}

// Monitor health
const metrics = client.getMetrics();
console.log('Circuit breaker state:', metrics.circuitBreaker.state);
console.log('Active requests:', metrics.bulkhead.activeCount);
console.log('Available rate limit tokens:', metrics.rateLimiter.availableTokens);
```

---

## Tool-Call Loop Detection

**Problem:** An agent repeatedly calls the same tool with identical or near-identical parameters — a loop caused by insufficient directive strength, ambiguous responses, or a missing `ask_clarify` branch. Without server-side detection, loops burn tokens until the context window or API budget is exhausted.

**Solution:** Track per-session call fingerprints server-side. If the same tool is called >3 times within 60 seconds with semantically equivalent inputs, return a structured break-loop response instead of executing.

```typescript
interface LoopDetectorConfig {
  windowMs: number;       // Detection window (default: 60_000ms)
  threshold: number;      // Max calls before loop detection fires (default: 3)
}

export class ToolCallLoopDetector {
  private callLog = new Map<string, number[]>();  // fingerprint → [timestamps]
  private config: LoopDetectorConfig;

  constructor(config: LoopDetectorConfig = { windowMs: 60_000, threshold: 3 }) {
    this.config = config;
  }

  // Returns true if this call appears to be a loop
  isLoop(toolName: string, params: Record<string, unknown>): boolean {
    const fingerprint = `${toolName}:${JSON.stringify(params)}`;
    const now = Date.now();
    const window = this.config.windowMs;

    const timestamps = (this.callLog.get(fingerprint) ?? [])
      .filter(t => now - t < window);

    timestamps.push(now);
    this.callLog.set(fingerprint, timestamps);

    return timestamps.length > this.config.threshold;
  }

  // Use in tool handler wrapper
  breakLoopResponse(toolName: string) {
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          error: 'TOOL_CALL_LOOP_DETECTED',
          tool: toolName,
          message: `${toolName} was called with identical parameters more than ${this.config.threshold} times in ${this.config.windowMs / 1000} seconds.`,
          next: {
            intent: 'ask_clarify',
            prompt_template: `The agent appears to be in a loop calling ${toolName}. Ask the user: "I seem to be stuck trying to accomplish this. Could you clarify what outcome you need? The last attempt returned [insert last result]."`,
            suggested_tool: null,
            suggested_params: null,
          }
        })
      }]
    };
  }
}
```

### Usage in Tool Handler

```typescript
const loopDetector = new ToolCallLoopDetector();

server.registerTool('search_vendors', { ... }, async (params) => {
  if (loopDetector.isLoop('search_vendors', params)) {
    return loopDetector.breakLoopResponse('search_vendors');
  }
  // ... normal implementation
});
```

**Loop detection is per-session, not per-user.** Use the MCP session ID (available in the request context) as the scoping key — an agent retrying across sessions is valid behavior; retrying within one session is a loop signal.
