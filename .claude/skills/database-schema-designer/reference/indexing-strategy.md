# Indexing Strategy

Plan and implement database indexes to optimize query performance without degrading write throughput.

---

## When to Create Indexes

| Always Index | Reason |
|--------------|--------|
| Foreign keys | Speed up JOINs |
| WHERE clause columns | Speed up filtering |
| ORDER BY columns | Speed up sorting |
| Unique constraints | Enforce uniqueness |

```sql
-- Foreign key index
CREATE INDEX idx_orders_customer ON orders(customer_id);

-- Query pattern index
CREATE INDEX idx_orders_status_date ON orders(status, created_at);
```

---

## Index Types

| Type | Best For | Example Query |
|------|----------|---------------|
| B-Tree | Ranges, equality, sorting | `price > 100`, `ORDER BY created_at` |
| Hash | Exact matches only | `email = 'x@y.com'` |
| Full-text | Text search | `MATCH AGAINST ('search term')` |
| Partial | Subset of rows | `WHERE is_active = true` |
| GIN | Array/JSONB containment | `tags @> ARRAY['urgent']` |
| GiST | Geometric/range queries | PostGIS geospatial |

### B-Tree (Default)

Most common index type. Supports equality, range, and sorting operations.

```sql
CREATE INDEX idx_orders_created ON orders(created_at);

-- Supports:
-- WHERE created_at = '2025-01-01'
-- WHERE created_at > '2025-01-01'
-- ORDER BY created_at DESC
```

### Partial Index

Index only rows matching a condition. Smaller index, faster queries on the subset.

```sql
-- Only index active users (PostgreSQL)
CREATE INDEX idx_active_users ON users(email)
WHERE is_active = true;

-- Useful when most queries filter on a specific condition
```

---

## Composite Index Order

Column order in composite indexes determines which queries can use the index.

```sql
CREATE INDEX idx_customer_status ON orders(customer_id, status);

-- Uses index (leftmost prefix match)
SELECT * FROM orders WHERE customer_id = 123;
SELECT * FROM orders WHERE customer_id = 123 AND status = 'pending';

-- Does NOT use index (skips leftmost column)
SELECT * FROM orders WHERE status = 'pending';
```

### Column Order Rules

1. **Equality columns first** -- columns compared with `=`
2. **Range columns last** -- columns compared with `>`, `<`, `BETWEEN`
3. **Most selective first** -- column with highest cardinality when all else is equal
4. **Most queried alone first** -- column most commonly used without the other columns

```sql
-- Query: WHERE status = 'active' AND created_at > '2025-01-01'
-- Best order: (status, created_at) -- equality first, then range
CREATE INDEX idx_status_date ON orders(status, created_at);
```

---

## Index Pitfalls

| Pitfall | Problem | Solution |
|---------|---------|----------|
| Over-indexing | Slow writes, wasted storage | Only index what queries need |
| Wrong column order | Index not used | Match query patterns |
| Missing FK indexes | Slow JOINs and cascading deletes | Always index foreign keys |
| Indexing low-cardinality columns | Index not useful | Skip columns with few distinct values (except in composite) |
| Functions on indexed columns | Index bypassed | Use functional indexes or restructure query |

```sql
-- BAD: Function prevents index use
SELECT * FROM users WHERE LOWER(email) = 'user@example.com';

-- GOOD: Functional index (PostgreSQL)
CREATE INDEX idx_users_email_lower ON users(LOWER(email));

-- GOOD: Store normalized data
-- Store email already lowercased, index the column directly
```

---

## Query Analysis with EXPLAIN

Use EXPLAIN to verify indexes are being used.

```sql
EXPLAIN SELECT * FROM orders
WHERE customer_id = 123 AND status = 'pending';
```

| Look For | Meaning |
|----------|---------|
| type: ALL | Full table scan (bad) |
| type: ref | Index used (good) |
| type: range | Index range scan (good) |
| key: NULL | No index used |
| rows: high | Many rows scanned |

### Optimization Workflow

1. **Identify slow queries** -- check slow query log or application monitoring
2. **Run EXPLAIN** -- see current execution plan
3. **Add index** -- based on WHERE, JOIN, ORDER BY columns
4. **Re-run EXPLAIN** -- verify index is used
5. **Benchmark** -- measure actual improvement

---

## Performance Considerations

| Technique | When to Use |
|-----------|-------------|
| Add indexes | Slow WHERE/ORDER BY queries |
| Remove unused indexes | Write-heavy tables with unused indexes |
| Covering indexes | Avoid table lookups for frequent queries |
| Pagination | Large result sets (LIMIT/OFFSET or cursor) |
| Partitioning | Very large tables (100M+ rows) |

### N+1 Query Problem

```python
# BAD: N+1 queries
orders = db.query("SELECT * FROM orders")
for order in orders:
    customer = db.query(f"SELECT * FROM customers WHERE id = {order.customer_id}")

# GOOD: Single JOIN
results = db.query("""
    SELECT orders.*, customers.name
    FROM orders
    JOIN customers ON orders.customer_id = customers.id
""")
```

---

## Index Maintenance

- **Monitor index usage** -- drop indexes that are never read
- **Rebuild bloated indexes** -- REINDEX in PostgreSQL, OPTIMIZE TABLE in MySQL
- **Track index size** -- large indexes slow down writes and backups
- **Review after schema changes** -- new queries may need new indexes
