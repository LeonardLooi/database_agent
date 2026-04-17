## Rate Limiter

### Token Bucket Algorithm

```typescript
interface RateLimiterConfig {
  maxRequests: number;    // Max requests per window
  windowMs: number;       // Time window in ms
  burstSize: number;      // Max burst capacity
}

export class RateLimiter {
  private tokens: number;
  private lastRefill: number;

  constructor(private config: RateLimiterConfig) {
    this.tokens = config.burstSize;
    this.lastRefill = Date.now();
  }

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    this.refillTokens();

    if (this.tokens < 1) {
      throw new Error('Rate limit exceeded');
    }

    this.tokens--;
    return fn();
  }

  private refillTokens(): void {
    const now = Date.now();
    const timePassed = now - this.lastRefill;
    const refillRate = this.config.maxRequests / this.config.windowMs;
    const tokensToAdd = timePassed * refillRate;

    this.tokens = Math.min(this.config.burstSize, this.tokens + tokensToAdd);
    this.lastRefill = now;
  }

  getMetrics() {
    this.refillTokens();
    return {
      availableTokens: Math.floor(this.tokens),
      maxTokens: this.config.burstSize,
      refillRate: this.config.maxRequests / (this.config.windowMs / 1000),
    };
  }

  reset(): void {
    this.tokens = this.config.burstSize;
    this.lastRefill = Date.now();
  }
}
```

## Retry Strategy

### Exponential Backoff with Jitter

```typescript
interface RetryConfig {
  maxAttempts: number;         // Max retry attempts
  initialDelay: number;        // Initial delay in ms
  maxDelay: number;            // Max delay in ms
  backoffMultiplier: number;   // Multiplier for exponential backoff
  jitterFactor: number;        // Random jitter (0-1)
  retryableErrors: string[];   // Regex patterns for retryable errors
}

export class RetryStrategy {
  constructor(private config: RetryConfig) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    let lastError: Error | undefined;

    for (let attempt = 0; attempt < this.config.maxAttempts; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        if (!this.isRetryable(lastError)) {
          throw lastError;
        }

        if (attempt < this.config.maxAttempts - 1) {
          const delay = this.calculateDelay(attempt);
          await this.sleep(delay);
        }
      }
    }

    throw lastError || new Error('Retry failed');
  }

  private isRetryable(error: Error): boolean {
    return this.config.retryableErrors.some((pattern) => {
      const regex = new RegExp(pattern, 'i');
      return regex.test(error.message) || regex.test(error.name);
    });
  }
  // ↑ isRetryable uses an ALLOWLIST (not a denylist) of retryable error patterns.
  // Only errors matching a pattern are retried — everything else is thrown immediately.
  // CRITICAL: 4xx HTTP errors (400, 401, 403, 404, 422) must NEVER appear in
  // retryableErrors. 4xx means the request is wrong — retrying it wastes quota
  // and will always fail. Only include network-level errors and 5xx (transient
  // server failures) plus 429 (rate-limited — retry after backoff).

  private calculateDelay(attempt: number): number {
    const exponentialDelay = Math.min(
      this.config.initialDelay * Math.pow(this.config.backoffMultiplier, attempt),
      this.config.maxDelay
    );

    const jitter = exponentialDelay * this.config.jitterFactor * Math.random();
    return Math.floor(exponentialDelay + jitter);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
```

## Caching (LRU with TTL)

Use caching for read-heavy tools that call slow upstream services (vendor profiles, search results, external API lookups). Cache the upstream response, not the MCP tool result.

### Design Rules

- **LRU eviction** — bounded memory; oldest entries evicted when capacity is reached
- **TTL per resource type** — volatile data (availability, prices) short TTL (60s); stable data (profiles, metadata) longer TTL (5min)
- **Track hit/miss ratio** — expose via metrics so you can tune TTL and capacity
- **Cache key** — deterministic hash of the inputs that determine uniqueness (not the full input object)
- **Never cache errors** — only cache successful responses; a failed upstream call should not poison the cache
- **Invalidate on write** — if a tool call mutates state, invalidate related cache entries immediately

### Implementation

```typescript
import { LRUCache } from 'lru-cache';

interface CacheConfig {
  vendorProfileMaxSize: number;   // max entries
  vendorProfileTtlMs: number;     // 5 min for stable profile data
  availabilityMaxSize: number;
  availabilityTtlMs: number;      // 1 min for volatile availability data
}

export const DEFAULT_CACHE_CONFIG: CacheConfig = {
  vendorProfileMaxSize: 500,
  vendorProfileTtlMs: 5 * 60 * 1000,   // 5 minutes
  availabilityMaxSize: 1000,
  availabilityTtlMs: 60 * 1000,         // 1 minute
};

interface CacheStats {
  hits: number;
  misses: number;
  hitRatio: number;
  size: number;
}

export class VendorCache {
  private readonly profileCache: LRUCache<string, unknown>;
  private readonly availabilityCache: LRUCache<string, unknown>;
  private hits = 0;
  private misses = 0;

  constructor(config: CacheConfig) {
    this.profileCache = new LRUCache({
      max: config.vendorProfileMaxSize,
      ttl: config.vendorProfileTtlMs,
    });
    this.availabilityCache = new LRUCache({
      max: config.availabilityMaxSize,
      ttl: config.availabilityTtlMs,
    });
  }

  getProfile<T>(key: string): T | undefined {
    const hit = this.profileCache.get(key) as T | undefined;
    hit !== undefined ? this.hits++ : this.misses++;
    return hit;
  }

  setProfile<T>(key: string, value: T): void {
    this.profileCache.set(key, value);
  }

  getAvailability<T>(key: string): T | undefined {
    const hit = this.availabilityCache.get(key) as T | undefined;
    hit !== undefined ? this.hits++ : this.misses++;
    return hit;
  }

  setAvailability<T>(key: string, value: T): void {
    this.availabilityCache.set(key, value);
  }

  getStats(): CacheStats {
    const total = this.hits + this.misses;
    return {
      hits: this.hits,
      misses: this.misses,
      hitRatio: total > 0 ? this.hits / total : 0,
      size: this.profileCache.size + this.availabilityCache.size,
    };
  }
}
```

### Usage in Tool Handler

```typescript
// Check cache before calling upstream
const cacheKey = `vendor:${vendorId}`;
const cached = cache.getProfile<VendorProfile>(cacheKey);
if (cached) {
  return { ...cached, cache_hit: true };
}

// Cache miss — call upstream, store on success only
const profile = await upstreamClient.getVendorProfile(vendorId);
cache.setProfile(cacheKey, profile);
return { ...profile, cache_hit: false };
```

### Metrics to Expose

Track and expose `cache_hits_total` and `cache_misses_total` as Prometheus counters so you can observe the hit ratio over time and tune TTL/capacity accordingly.

---
