# PostgreSQL Review Checklist

## 1. Query Performance (CRITICAL)

- All WHERE/JOIN columns have appropriate indexes
- Correct index type chosen (B-tree for equality/range, GIN for JSONB/arrays/full-text, BRIN for time-series)
- Composite indexes have correct column order (equality columns first, then range)
- No N+1 query patterns — use JOINs or `ANY(ARRAY[...])` instead
- No `SELECT *` in production code
- Cursor-based pagination instead of OFFSET on large tables
- Batch inserts instead of individual inserts for bulk operations
- EXPLAIN ANALYZE run on complex queries; no unexpected Seq Scans on large tables
- Covering indexes (INCLUDE) used where beneficial
- Partial indexes for commonly filtered subsets (soft deletes, status filters)

## 2. Schema Design (HIGH)

- `bigint` for IDs (not `int`), or UUIDv7 for distributed systems (not random UUIDs)
- `text` for strings (not `varchar(n)` unless constraint needed)
- `timestamptz` for timestamps (not `timestamp`)
- `numeric` for money (not `float`)
- `boolean` for flags (not `varchar`)
- Primary keys defined on all tables
- Foreign keys with appropriate ON DELETE behavior
- NOT NULL where appropriate, CHECK constraints for validation
- `lowercase_snake_case` identifiers (no quoted mixed-case)
- Partitioning considered for tables > 100M rows or time-series data

## 3. Security & RLS (CRITICAL)

- RLS enabled and forced on multi-tenant tables
- RLS policies use `(SELECT auth.uid())` pattern (not bare function call per row)
- RLS policy columns are indexed
- Least privilege: no `GRANT ALL` to application users
- Public schema permissions revoked; roles scoped to needed operations
- Sensitive data encrypted; PII access logged
- All queries parameterized (no SQL injection risk)

> For application-level security beyond database (OWASP Top 10, secrets detection, auth bypasses, XSS, SSRF), delegate to the `security-reviewer` agent.

## 4. Concurrency & Connections (MEDIUM)

- Transactions kept short; no external API calls while holding locks
- Consistent lock ordering to prevent deadlocks
- SKIP LOCKED used for queue/worker patterns
- Connection pooling configured (transaction mode for most apps)
- Idle timeouts set (`idle_in_transaction_session_timeout`, `idle_session_timeout`)
- UPSERT (`ON CONFLICT`) used instead of check-then-insert patterns

## 5. Monitoring & Maintenance

- `pg_stat_statements` enabled for query analysis
- Autovacuum tuned for high-churn tables
- Statistics kept current (`ANALYZE` run regularly)

## Anti-Patterns to Always Flag

- `SELECT *` in production code
- Missing indexes on foreign keys
- OFFSET pagination on large tables
- N+1 query patterns
- `int` IDs, `varchar(255)`, `timestamp` (no tz), `timetz`, `char(n)`, `money`, `serial`, `float` for money
- `GRANT ALL` to application users
- RLS policies with bare `auth.uid()` (not wrapped in SELECT)
- Locks held during external calls
- Unparameterized queries

## Output Format

Report findings grouped by severity (CRITICAL > HIGH > MEDIUM > LOW) with file location, issue description, and recommended fix. Include the review checklist with pass/fail status.
