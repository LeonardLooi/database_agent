# Agentic AI 4-Tier Caching Patterns

Production-tested caching architecture from the weather-ai-agent-service. Adapt patterns and class names to your domain.

## Cache Hierarchy Overview

| Tier | Name | Latency | TTL | Scope | Hit Rate |
|------|------|---------|-----|-------|----------|
| Q1 | In-memory LRU | <1ms | 5 min (300s) | Server-local, user-specific | 15-25% |
| Q2 | Redis distributed | <10ms | 30 min (1800s) | Shared across servers, query-level | 30-40% |
| Q3 | Qdrant semantic | <50ms | 30 min (1800s) | Similarity match (threshold 0.85) | +25-40% |
| L3 | Anthropic Prompt Cache | automatic | API-managed | API-level, 50-90% cost reduction | N/A |

**Source:** `orchestrator.py` docstring lines 4-7, `l1_memory_cache.py` lines 5-8, `l2_redis_cache.py` lines 5-9, `semantic_query_cache.py` lines 18-24.

## Cache Flow

```
Query arrives
    |
    v
Q1 (in-memory LRU) --- HIT --> Return immediately (<1ms)
    |
   MISS
    |
    v
Q2 (Redis) --- HIT --> Backfill Q1 + Return (<10ms)
    |
   MISS
    |
    v
Q3 (Qdrant semantic) --- HIT --> Backfill Q1 + Backfill Q2 + Return (<50ms)
    |
   MISS
    |
    v
Execute agent (with L3 Anthropic prompt cache)
    |
    v
Write to Q1 + Q2 + Q3
```

**Source:** `orchestrator.py` lines 196-295 (get method), lines 338-359 (set method).

## CacheResult Dataclass

```python
@dataclass
class CacheResult:
    """Result from cache lookup with metadata."""
    response: str
    cache_tier: str  # "Q1", "Q2", "Q3", or "MISS"
    latency_ms: float
    cache_key: str = ""
```

**Source:** `orchestrator.py` lines 50-57.

## CacheOrchestrator — Core API

```python
orchestrator = CacheOrchestrator(
    l1_cache=QueryCache(max_size=1000),          # Q1: in-memory
    l2_cache=RedisQueryCache(),                   # Q2: Redis
    q3_cache=semantic_cache,                      # Q3: Qdrant
    enable_tracing=True,                          # LangSmith
    enable_metrics=True,                          # Prometheus
)

# Try cache first (Q1 → Q2 → Q3)
cached = await orchestrator.get(query, user_id, enable_rag, enable_cot)
if cached:
    return cached.response  # cache_tier tells you which tier hit

# Cache miss — execute agent
response = await execute_agent(...)

# Write to all tiers
await orchestrator.set(query, user_id, enable_rag, enable_cot, response)

# Invalidate a specific entry
result = await orchestrator.invalidate(query, user_id, enable_rag, enable_cot)
# returns {"q1": bool, "q2": bool, "q3": bool}
```

**Source:** `orchestrator.py` lines 142-163 (`__init__`), 174-180 (`get` signature), 317-334 (`set` signature), 367-387 (`invalidate` signature).

## Q1: In-Memory LRU Cache

**File:** `cache/l1_memory_cache.py`

```python
from backend.src.cache.l1_memory_cache import QueryCache

cache = QueryCache(max_size=1000, ttl_seconds=300)

# Get — returns None on miss or life-safety bypass
response = cache.get(query, user_id, enable_rag, enable_cot)

# Set — silently skips life-safety queries
cache.set(query, user_id, enable_rag, enable_cot, response)
```

**Key design:** User-specific — `user_id` is included in the cache key, so different users get separate cache entries for the same query. Max 1000 entries (~2MB). LRU eviction by oldest timestamp.

**Source:** `l1_memory_cache.py` lines 38-43, 66-76.

## Q2: Redis Distributed Cache

**File:** `cache/l2_redis_cache.py`

```python
from backend.src.cache.l2_redis_cache import RedisQueryCache

cache = RedisQueryCache(
    redis_url="redis://localhost:6379/0",
    ttl_seconds=1800,
    key_prefix="weather:cache:",
)
await cache.connect()

# Async get/set
response = await cache.get(query, user_id, enable_rag, enable_cot)
await cache.set(query, user_id, enable_rag, enable_cot, response)
await cache.close()
```

**Key design:** Query-level — `user_id` is intentionally excluded from the key, enabling cross-user cache sharing. The same query from two different users hits the same cache entry.

**Source:** `l2_redis_cache.py` lines 43-58, 144-190.

## Q3: Semantic Cache (Qdrant)

**File:** `cache/semantic_query_cache.py`

```python
from backend.src.cache.semantic_query_cache import create_semantic_query_cache

# Factory creates all dependencies (Redis, Qdrant, embeddings, promoter)
q3_cache = await create_semantic_query_cache(
    redis_url="redis://localhost:6379/0",
    qdrant_url="http://localhost:6333",
    ttl=1800,
    threshold=0.85,  # cosine similarity minimum
)

# Lookup — returns TwoTierCacheResult
result = await q3_cache.get_response(query, enable_rag, enable_cot)
if result.hit:
    return result.value  # dict {"response": "..."}

# Store
await q3_cache.set_response(
    query=query,
    response={"response": response_text},
    enable_rag=enable_rag,
    enable_cot=enable_cot,
)
```

**Key design:** Normalizes query before embedding (`QueryNormalizer`). Uses `CacheKeyGenerator` with `q3:` prefix for exact-match tier within Q3. Similarity threshold 0.85 — "SF weather" matches "San Francisco weather".

**Source:** `semantic_query_cache.py` lines 77-113, 115-134, 136-153, 274-332.

## Cache Key Generation — SHA-256 Pattern

All tiers use SHA-256 hashing for cache keys. Shared utility `CacheKeyGenerator`:

```python
from backend.src.cache.common import CacheKeyGenerator

# From string
key = CacheKeyGenerator.generate("weather in Miami", prefix="query:")
# Returns: "query:a1b2c3d4e5f6g7h8"  (16-char truncated SHA-256)

# From dict (tool arguments)
key = CacheKeyGenerator.from_dict({"location": "Miami", "days": 7}, prefix="tool:")

# From tool call
key = CacheKeyGenerator.from_tool_call("get_forecast", {"location": "Miami"})
# Returns: "tool:e7f8g9h0i1j2k3l4"

# From query with feature flags
key = CacheKeyGenerator.from_query(query, enable_rag=True, enable_cot=True)
```

**Normalization applied before hashing:** `input.strip().lower()`. Keys are sorted by `json.dumps(data, sort_keys=True)` before hashing for determinism.

**L1 key includes:** `query`, `user_id`, `enable_rag`, `enable_cot` — user-specific.
**L2 key includes:** `query`, `enable_rag`, `enable_cot` — `user_id` excluded for cross-user sharing.

**Not included in any key:** `session_id`, timestamp — these are too variable and would cause cache misses.

**Source:** `cache_key_generator.py` lines 1-10, 43-71, 73-102, 104-132, 162-192. `l1_memory_cache.py` lines 103-143. `l2_redis_cache.py` lines 144-190.

## Backfill / Promotion Pattern

When a cache hit occurs at Q2 or Q3, the result is written back to the faster tiers automatically:

```python
# Q2 hit → backfill Q1
if l2_result:
    l1.set(query, user_id, enable_rag, enable_cot, l2_result)  # warm local cache
    stats.l1_backfills += 1

# Q3 hit → backfill Q1 and Q2
if q3_result.hit:
    l1.set(query, user_id, enable_rag, enable_cot, response_text)
    await l2.set(query, user_id, enable_rag, enable_cot, response_text)
    stats.l1_backfills += 1
    stats.l2_backfills += 1
```

**CachePromoter** handles Q3 → exact-match tier promotion using `redis.setex`:

```python
from backend.src.cache.common import CachePromoter

promoter = CachePromoter()
success = await promoter.promote(
    redis=redis_client,
    cache_key="q3:abc123...",
    value=serialized_response,
    ttl=1800,
)
# Batch promotion also available: promoter.promote_batch(redis, entries)
```

**Source:** `orchestrator.py` lines 229-233, 267-273. `cache_promoter.py` lines 59-90.

## @cached_tool Decorator

Zero code-change caching for any async tool function:

```python
from backend.src.cache.tool_cache import cached_tool, set_tool_cache

# Configure once at startup
set_tool_cache(tool_result_cache_instance)

# Apply to any async tool
@cached_tool("get_forecast")
async def get_forecast(location: str, days: int = 7) -> dict:
    """Get weather forecast — automatically cached."""
    return await weather_mcp_client.call("get_forecast", {
        "location": location,
        "days": days,
    })

# Normal call (cache lookup + store)
result = await get_forecast("Miami", days=7)

# Force refresh (bypass cache, re-fetch and re-cache)
result = await get_forecast("Miami", days=7, force_refresh=True)

# Life-safety tools — NEVER apply @cached_tool
async def get_hurricane_alerts(location: str) -> dict:
    """Hurricane alerts — no caching, always fresh."""
    return await hurricane_mcp_client.call("get_hurricane_alerts", {"location": location})
```

**How it works:** The decorator uses `inspect.signature` to map positional args to parameter names, builds `tool_args` dict, calls `ToolResultCache.get_tool_result(tool_name, tool_args, force_refresh)`, and on miss calls the wrapped function then stores the result.

**Source:** `cached_tool_decorator.py` lines 15-42 (usage example), 84-168 (implementation).

## Life-Safety Bypass — Non-Negotiable

Hurricane and emergency queries bypass ALL cache tiers at both read and write. This check runs first, before any key generation or Redis call:

```python
LIFE_SAFETY_KEYWORDS = {
    "hurricane", "hurricanes",
    "evacuation", "evacuate", "evacuating",
    "emergency", "emergencies",
    "alert", "alerts", "warning", "warnings",
    "storm surge", "landfall",
    "category 3", "category 4", "category 5", "cat 3", "cat 4", "cat 5",
    "evacuation zone", "evacuation order",
    "shelter", "shelters",
    "life-threatening", "life threatening",
    "dangerous", "danger",
}

def _is_life_safety_query(self, query: str) -> bool:
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in self.LIFE_SAFETY_KEYWORDS)
```

Both `QueryCache` (Q1) and `RedisQueryCache` (Q2) implement this independently. On bypass, `bypasses` counter is incremented for monitoring. **Do not apply `@cached_tool` to life-safety tools.**

**Source:** `l1_memory_cache.py` lines 52-64, 88-101, 165-171, 219-225. `l2_redis_cache.py` lines 61-72, 102-115, 213-218, 272-277.

## Prometheus Metrics Integration

The orchestrator records hits and misses to Prometheus via `get_cache_metrics()`:

```python
# Called on every Q1/Q2 hit
metrics.record_hit(
    cache_type="query",     # "query" | "tool" | "llm"
    tier="tier1",           # "tier1" (exact) | "tier2" (semantic)
    similarity=None,        # float for Q3 semantic hits
    latency_ms=latency_ms,
)

# Called on every cache miss
metrics.record_miss(cache_type="query", latency_ms=latency_ms)
```

Example Prometheus queries for dashboards:

```
# Cache hit rate
sum(rate(weather_cache_hit_total[5m])) / sum(rate(weather_cache_requests_total[5m]))

# Cost savings
sum(weather_cache_cost_savings_usd)

# Cache latency p95
histogram_quantile(0.95, sum(rate(cache_latency_seconds_bucket[5m])) by (le))
```

**Source:** `orchestrator.py` lines 539-596 (`_record_cache_hit`, `_record_cache_miss`). Prometheus module: `backend.src.observability.cache_metrics`.

## CacheStats — Hit Rate Tracking

```python
stats = orchestrator.get_stats()
# Returns:
# {
#   "orchestrator": {
#     "total_requests": int,
#     "q1_hits": int, "q2_hits": int, "q3_hits": int,
#     "q1_backfills": int, "q2_backfills": int,
#     "cache_misses": int,
#     "q1_hit_rate": float, "q2_hit_rate": float,
#     "q3_hit_rate": float, "overall_hit_rate": float,
#   },
#   "q1": {...},   # QueryCache.get_stats()
#   "q2": {...},   # RedisQueryCache stats
#   "q3": {...},   # {"enabled": bool, "type": "semantic", "collection": str}
# }

orchestrator.reset_stats()
```

**Source:** `orchestrator.py` lines 60-117 (`CacheStats`), 450-495 (`get_stats`).

## Wiring All Tiers Together

```python
# Startup sequence
l1 = QueryCache(max_size=1000, ttl_seconds=300)

l2 = RedisQueryCache(redis_url=settings.redis_url, ttl_seconds=1800)
await l2.connect()

q3 = await create_semantic_query_cache(
    redis_url=settings.redis_url,
    qdrant_url=settings.qdrant_url,
)

orchestrator = CacheOrchestrator(
    l1_cache=l1,
    l2_cache=l2,
    q3_cache=q3,
    enable_tracing=settings.langsmith_enabled,
    enable_metrics=True,
)

# Any tier can be None — orchestrator degrades gracefully
# e.g., CacheOrchestrator(l1_cache=l1) — Q2 and Q3 disabled
```

## Performance Expectations

| Scenario | Expected Latency |
|----------|-----------------|
| Q1 hit | <1ms |
| Q2 hit | <10ms |
| Q3 hit | <50ms |
| Full miss (agent execution) | 1000-5000ms |
| Q1 hit rate | 15-25% |
| Q2 hit rate (among Q1 misses) | 30-40% |
| Q3 additional hit rate | 25-40% |
| L3 Anthropic cost reduction | 50-90% |

**Source:** `orchestrator.py` lines 4-7, `l1_memory_cache.py` lines 5-8, `l2_redis_cache.py` lines 5-9, `semantic_query_cache.py` lines 18-24.

---

**Reference:** Patterns from weather-ai-agent-service `backend/src/cache/`. Adapt class names, TTLs, thresholds, and keyword lists to your domain.
