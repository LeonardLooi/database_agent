# SQL Optimization Patterns — Implementation Playbook

Detailed SQL code, EXPLAIN annotation guides, and monitoring queries for the `sql-optimization-patterns` skill.

---

## 1. Reading EXPLAIN Output

Understanding EXPLAIN output is fundamental to all optimization.

```sql
-- Basic EXPLAIN (estimated costs only)
EXPLAIN SELECT * FROM users WHERE email = 'user@example.com';

-- With actual execution stats (required for real optimization)
EXPLAIN ANALYZE
SELECT * FROM users WHERE email = 'user@example.com';

-- Full detail: actual stats + buffer hits + verbose output
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT u.*, o.order_total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.created_at > NOW() - INTERVAL '30 days';
```

**Key Metrics:**

| Node | Meaning | Action |
|------|---------|--------|
| `Seq Scan` | Full table scan | Add index on filtered column |
| `Index Scan` | Using index, fetches heap rows | Good — verify column order |
| `Index Only Scan` | Index covers all needed columns | Best — no heap access needed |
| `Nested Loop` | Join via iteration | OK for small outer; bad for large outer |
| `Hash Join` | Build hash table, probe it | Good for larger datasets |
| `Merge Join` | Merge two sorted inputs | Good when both sides sorted |
| `cost=X..Y` | Estimated startup..total cost | Lower is better |
| `rows=N` | Estimated rows | Compare to `Actual Rows` — large divergence = stale stats |
| `Actual Time=X..Y ms` | Real execution time per loop | The authoritative number |
| `Buffers: hit=N read=N` | Cache hits vs disk reads | High `read` = cache miss, consider shared_buffers |

---

## 2. Index Strategies

### Index Types

```sql
-- B-Tree (default) — equality, range, ORDER BY
CREATE INDEX idx_users_email ON users(email);

-- Composite index — multi-column WHERE (order matters: equality first, range last)
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- Partial index — index a subset of rows (saves space, faster for filtered queries)
CREATE INDEX idx_active_users ON users(email)
WHERE status = 'active';

-- Expression index — index on a function result
CREATE INDEX idx_users_lower_email ON users(LOWER(email));

-- Covering index — include extra columns to enable Index Only Scan
CREATE INDEX idx_users_email_covering ON users(email)
INCLUDE (name, created_at);

-- GIN — full-text search, arrays, JSONB containment
CREATE INDEX idx_posts_search ON posts
USING GIN(to_tsvector('english', title || ' ' || body));

-- GIN for JSONB
CREATE INDEX idx_metadata ON events USING GIN(metadata);

-- BRIN — block range index for very large tables with physical correlation (e.g., append-only logs)
CREATE INDEX idx_logs_created ON logs USING BRIN(created_at);
```

### Composite Index Column Order Rule

```
Equality columns FIRST → Range columns LAST → Most selective FIRST
```

Example: `WHERE user_id = $1 AND status = $2 AND created_at > $3`
```sql
-- Correct order: equality (user_id, status) first, range (created_at) last
CREATE INDEX idx_orders_user_status_date ON orders(user_id, status, created_at);
-- Wrong order: range first blocks use of subsequent columns
-- CREATE INDEX ... ON orders(created_at, user_id, status);  -- BAD
```

### When NOT to Index

- Columns with very low cardinality (e.g., `boolean`, `status` with 2 values) — consider partial index instead
- Tables with <1,000 rows — sequential scan is faster
- Columns only in SELECT, not WHERE/JOIN/ORDER BY
- Already covered by a composite index as a prefix

---

## 3. Pattern 1 — Eliminate N+1 Queries

**Problem: N+1 Anti-Pattern**
```python
# Bad: Executes N+1 queries (1 for users + N for each user's orders)
users = db.query("SELECT * FROM users LIMIT 10")
for user in users:
    orders = db.query("SELECT * FROM orders WHERE user_id = ?", user.id)
    # This runs 11 queries total for 10 users
```

**Fix: Single JOIN**
```sql
-- One query replaces N+1
SELECT
    u.id, u.name, u.email,
    o.id AS order_id, o.total, o.created_at
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10);
```

**Fix: Batch Load (when JOIN produces too many rows due to multiplicity)**
```python
# Two queries instead of N+1
users = db.query("SELECT * FROM users LIMIT 10")
user_ids = [u.id for u in users]

# Batch load all orders in one query
orders = db.query(
    "SELECT * FROM orders WHERE user_id = ANY($1::int[])",
    user_ids
)

# Group in Python
from collections import defaultdict
orders_by_user = defaultdict(list)
for order in orders:
    orders_by_user[order.user_id].append(order)
```

**SQLAlchemy (Python) Fix:**
```python
# Use selectinload for async — avoids N+1 without JOIN multiplicity
from sqlalchemy.orm import selectinload

result = await session.execute(
    select(User).options(selectinload(User.orders)).limit(10)
)
users = result.scalars().all()
```

**Prisma (NestJS) Fix:**
```typescript
// Use include to eager-load in a single query
const users = await prisma.user.findMany({
    take: 10,
    include: { orders: true }
});
```

---

## 4. Pattern 2 — Cursor-Based Pagination

**Problem: OFFSET on Large Tables**
```sql
-- Extremely slow for large offsets — database scans and discards all prior rows
SELECT * FROM users
ORDER BY created_at DESC
LIMIT 20 OFFSET 100000;  -- Scans 100,020 rows, returns 20
```

**Fix: Cursor-Based Pagination**
```sql
-- First page (no cursor)
SELECT id, name, email, created_at
FROM users
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- Subsequent pages (use last row's values as cursor)
SELECT id, name, email, created_at
FROM users
WHERE (created_at, id) < ('2024-01-15 10:30:00', 12345)  -- cursor from last row
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- Required index (must match ORDER BY exactly)
CREATE INDEX idx_users_cursor ON users(created_at DESC, id DESC);
```

**FastAPI Response Pattern:**
```python
class PaginatedResponse(BaseModel):
    items: list[UserResponse]
    next_cursor: str | None  # base64-encoded (created_at, id) tuple
    has_more: bool
```

---

## 5. Pattern 3 — Aggregate Optimization

**Optimize COUNT:**
```sql
-- Exact count (slow on large tables — full scan)
SELECT COUNT(*) FROM orders;

-- Fast estimate from statistics (good for display badges, ~1% accuracy)
SELECT reltuples::bigint AS estimate
FROM pg_class WHERE relname = 'orders';

-- Filtered count with index (fast when index exists on created_at)
SELECT COUNT(*) FROM orders
WHERE created_at > NOW() - INTERVAL '7 days';

-- Create supporting index if not present
CREATE INDEX idx_orders_created ON orders(created_at);
```

**Optimize GROUP BY:**
```sql
-- Bad: groups all rows, then filters by HAVING
SELECT user_id, COUNT(*) AS order_count
FROM orders
GROUP BY user_id
HAVING COUNT(*) > 10;

-- Better: filter before grouping when possible
SELECT user_id, COUNT(*) AS order_count
FROM orders
WHERE status = 'completed'  -- reduce rows before GROUP BY
GROUP BY user_id
HAVING COUNT(*) > 10;

-- Supporting composite index
CREATE INDEX idx_orders_user_status ON orders(user_id, status);
```

---

## 6. Pattern 4 — Subquery Optimization

**Transform Correlated Subqueries to JOINs:**
```sql
-- Bad: correlated subquery runs once per row in outer query
SELECT u.name, u.email,
    (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) AS order_count
FROM users u;

-- Good: single-pass aggregation with JOIN
SELECT u.name, u.email, COALESCE(agg.order_count, 0) AS order_count
FROM users u
LEFT JOIN (
    SELECT user_id, COUNT(*) AS order_count
    FROM orders
    GROUP BY user_id
) agg ON agg.user_id = u.id;

-- Also good: window function approach
SELECT DISTINCT ON (u.id)
    u.name, u.email,
    COUNT(o.id) OVER (PARTITION BY u.id) AS order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id;
```

**Use CTEs for Readability Without Performance Penalty (PostgreSQL 12+):**
```sql
-- CTE is inlined by default in PostgreSQL 12+ — no performance penalty
WITH recent_users AS (
    SELECT id, name, email
    FROM users
    WHERE created_at > NOW() - INTERVAL '30 days'
),
user_order_counts AS (
    SELECT user_id, COUNT(*) AS order_count
    FROM orders
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY user_id
)
SELECT ru.name, ru.email, COALESCE(uoc.order_count, 0) AS orders
FROM recent_users ru
LEFT JOIN user_order_counts uoc ON ru.id = uoc.user_id;

-- Force materialization only when needed (e.g., CTE used multiple times)
WITH recent_users AS MATERIALIZED (
    SELECT id FROM users WHERE created_at > NOW() - INTERVAL '30 days'
)
...
```

---

## 7. Pattern 5 — Batch Operations

**Batch INSERT:**
```sql
-- Bad: individual inserts in a loop (N round-trips)
INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');
INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com');

-- Good: single multi-row insert
INSERT INTO users (name, email) VALUES
    ('Alice', 'alice@example.com'),
    ('Bob', 'bob@example.com'),
    ('Carol', 'carol@example.com');

-- Best for bulk loads (PostgreSQL): COPY (no parsing overhead)
COPY users (name, email) FROM '/tmp/users.csv' CSV HEADER;

-- COPY via asyncpg (Python)
await conn.copy_records_to_table('users', records=user_tuples, columns=['name', 'email'])
```

**Batch UPDATE:**
```sql
-- Bad: individual updates in a loop
UPDATE users SET status = 'active' WHERE id = 1;
UPDATE users SET status = 'active' WHERE id = 2;

-- Good: single UPDATE with IN
UPDATE users SET status = 'active'
WHERE id IN (1, 2, 3, 4, 5);

-- Best for large batches: temp table join (avoids IN list limit and planner issues)
CREATE TEMP TABLE temp_user_updates (id INT, new_status TEXT);
INSERT INTO temp_user_updates VALUES (1, 'active'), (2, 'active'), ...;

UPDATE users u
SET status = t.new_status
FROM temp_user_updates t
WHERE u.id = t.id;

DROP TABLE temp_user_updates;
```

**UPSERT Pattern:**
```sql
-- Insert or update in one statement (no check-then-insert race condition)
INSERT INTO users (id, name, email, updated_at)
VALUES ($1, $2, $3, NOW())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    email = EXCLUDED.email,
    updated_at = NOW();
```

---

## 8. Materialized Views

Pre-compute expensive aggregations for read-heavy dashboards.

```sql
-- Create materialized view
CREATE MATERIALIZED VIEW user_order_summary AS
SELECT
    u.id,
    u.name,
    COUNT(o.id) AS total_orders,
    SUM(o.total) AS total_spent,
    MAX(o.created_at) AS last_order_date
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name;

-- Add index on the materialized view for fast lookups
CREATE INDEX idx_user_summary_spent ON user_order_summary(total_spent DESC);
CREATE INDEX idx_user_summary_id ON user_order_summary(id);

-- Refresh (blocks reads during refresh)
REFRESH MATERIALIZED VIEW user_order_summary;

-- Concurrent refresh (no read blocking — requires unique index)
CREATE UNIQUE INDEX idx_user_summary_unique_id ON user_order_summary(id);
REFRESH MATERIALIZED VIEW CONCURRENTLY user_order_summary;

-- Schedule refresh via pg_cron (if installed) or application cron job
-- Example: refresh every 15 minutes
SELECT cron.schedule('refresh-user-summary', '*/15 * * * *',
    'REFRESH MATERIALIZED VIEW CONCURRENTLY user_order_summary');
```

**Query the materialized view (very fast — pre-computed):**
```sql
SELECT id, name, total_spent
FROM user_order_summary
WHERE total_spent > 1000
ORDER BY total_spent DESC
LIMIT 50;
```

---

## 9. Table Partitioning

Split large tables for faster scans and maintenance.

```sql
-- Range partitioning by date (PostgreSQL 10+)
CREATE TABLE orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT NOT NULL,
    total NUMERIC(10,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create quarterly partitions
CREATE TABLE orders_2024_q1 PARTITION OF orders
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE orders_2024_q2 PARTITION OF orders
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

CREATE TABLE orders_2024_q3 PARTITION OF orders
    FOR VALUES FROM ('2024-07-01') TO ('2024-10-01');

CREATE TABLE orders_2024_q4 PARTITION OF orders
    FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');

-- Queries automatically scan only relevant partition (partition pruning)
SELECT * FROM orders
WHERE created_at BETWEEN '2024-02-01' AND '2024-02-28';
-- → Only scans orders_2024_q1, ignores all others

-- Create local indexes on each partition
CREATE INDEX idx_orders_2024_q1_user ON orders_2024_q1(user_id);
CREATE INDEX idx_orders_2024_q2_user ON orders_2024_q2(user_id);
-- Or use parent index (PostgreSQL 11+)
CREATE INDEX idx_orders_user ON orders(user_id);  -- propagates to all partitions
```

---

## 10. Monitoring Queries

### Find Slow Queries

```sql
-- Requires pg_stat_statements extension (enable in postgresql.conf: shared_preload_libraries = 'pg_stat_statements')
-- Top 10 slowest by mean execution time
SELECT
    LEFT(query, 100) AS query_preview,
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_ms,
    ROUND(mean_exec_time::numeric, 2) AS mean_ms,
    ROUND(stddev_exec_time::numeric, 2) AS stddev_ms
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Find Tables With Most Sequential Scans (Missing Indexes)

```sql
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    ROUND(seq_tup_read::numeric / NULLIF(seq_scan, 0), 0) AS avg_rows_per_seq_scan
FROM pg_stat_user_tables
WHERE seq_scan > 100  -- ignore tables rarely scanned
ORDER BY seq_tup_read DESC
LIMIT 10;
-- High seq_tup_read with low idx_scan = missing index candidate
```

### Find Unused Indexes (Candidates for Removal)

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND indexname NOT LIKE '%_pkey'  -- exclude primary keys
ORDER BY pg_relation_size(indexrelid) DESC;
-- Zero scans = wasting space and slowing writes — consider dropping
```

### Find Table Bloat (Candidates for VACUUM)

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    n_dead_tup,
    n_live_tup,
    ROUND(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 1) AS dead_pct,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC
LIMIT 10;
-- high dead_pct = run VACUUM ANALYZE <table>
```

---

## 11. Maintenance Commands

```sql
-- Update statistics (required after large data changes)
ANALYZE users;
ANALYZE VERBOSE orders;  -- shows rows sampled

-- Vacuum (reclaim dead rows — usually done automatically)
VACUUM ANALYZE users;
VACUUM FULL users;  -- compacts table (locks table — use during maintenance window)

-- Reindex (rebuild corrupt or bloated index)
REINDEX INDEX CONCURRENTLY idx_users_email;  -- non-blocking (PostgreSQL 12+)
REINDEX TABLE CONCURRENTLY users;            -- rebuilds all indexes non-blocking

-- Check index bloat
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 10;
```

---

## 12. Common Pitfalls Checklist

Before calling a query optimized, verify:

- [ ] `EXPLAIN (ANALYZE, BUFFERS)` run on actual data (not empty test DB)
- [ ] No `Seq Scan` on tables > 10,000 rows (unless intentional full scan)
- [ ] Composite index column order: equality → range → most selective first
- [ ] No function wrapping indexed column in WHERE clause
- [ ] No `LIKE '%prefix'` leading wildcard (use `pg_trgm` GIN if needed)
- [ ] Pagination uses cursor, not OFFSET
- [ ] N+1 eliminated (ORM eager load or batch query)
- [ ] Batch inserts/updates (not individual rows in loop)
- [ ] `ANALYZE` run after bulk data load (statistics are fresh)
- [ ] Index count reasonable (< 5 indexes per write-heavy table)
