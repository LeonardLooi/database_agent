---
name: sql-pro
description: "Masters modern SQL across PostgreSQL, BigQuery, Snowflake, and hybrid OLTP/OLAP systems — covering advanced query techniques, dimensional modeling, time-series SQL, and data warehouse patterns. Use when writing complex analytics SQL, designing cloud database schemas, or optimizing cross-platform SQL workloads."
argument-hint: "[query goal, schema, or workload type]"
allowed-tools: Read
context: fork
metadata:
  triggers: SQL expert, complex SQL, analytics SQL, HTAP, BigQuery SQL, Snowflake SQL, OLAP, OLTP, cloud database, dimensional modeling, time-series SQL, data warehouse, ETL SQL, SQL architecture
  related-skills: database-schema-designer, sql-optimization-patterns, python-dev, java-spring-api, nestjs-api, architecture-design
  domain: infrastructure
  role: architect
  scope: design
  output-format: document
last-reviewed: "2026-03-15"
---

## Iron Law
NEVER WRITE SQL WITHOUT KNOWING THE QUERY PLAN — USE EXPLAIN ANALYZE BEFORE CLAIMING A QUERY IS OPTIMIZED

## When to Use This Skill

- Writing complex SQL queries or analytics (window functions, recursive CTEs, OLAP)
- Designing SQL for cloud-native platforms (BigQuery, Snowflake, Redshift, Aurora)
- Building HTAP or hybrid analytical/transactional systems
- Migrating from OLTP-only PostgreSQL to an analytics tier
- Dimensional modeling, data vault, star/snowflake schemas
- Integrating machine learning with SQL workloads
- Time-series analysis (TimescaleDB, InfluxDB, Apache Druid)

## Do Not Use This Skill When

- You only need ORM-level guidance (use `python-dev`, `nestjs-api`, or `java-spring-api`)
- The system is non-SQL or document-only (use `database-schema-designer` for Firestore patterns)
- You need query optimization patterns for PostgreSQL OLTP (use `sql-optimization-patterns`)
- You cannot access query plans or schema details

## Quick Reference

| Workload | Platform | Key Consideration |
|----------|----------|-------------------|
| OLTP (transactional) | PostgreSQL | Normalize to 3NF, index FKs and WHERE cols |
| OLAP (analytics) | BigQuery / Snowflake / Redshift | Denormalize, columnar storage, partition by date |
| HTAP (both) | CockroachDB / TiDB | Read replicas for analytics, avoid read-your-own-writes latency |
| Time-series | TimescaleDB / InfluxDB | Hypertables, continuous aggregates, retention policies |
| Data warehouse | Redshift / Databricks | Star schema, materialized views, query concurrency |
| Graph + SQL | Neo4j / Amazon Neptune | Cypher for traversal, SQL for aggregation |

## Process

### Phase 1 — Understand the Workload
- Classify: OLTP / OLAP / HTAP / time-series / data warehouse
- Identify read/write ratio, peak concurrency, data volume (rows, GB)
- Confirm platform and version (PostgreSQL 16, BigQuery, Snowflake Enterprise, etc.)

### Phase 2 — Design the Query or Schema
- Apply appropriate normalization or denormalization for workload type
- For OLAP: star schema (fact + dimensions), SCD Type 2 for slowly changing dims
- For data vault: hubs, links, satellites pattern
- For event sourcing: append-only events table, aggregate projections

### Phase 3 — Optimize and Validate
- Run `EXPLAIN ANALYZE` (PostgreSQL) or query profile (BigQuery/Snowflake)
- Identify sequential scans, hash joins on large tables, spill to disk
- Apply indexes, partitioning, or materialization as evidence dictates

### Phase 4 — Production Readiness
- Use read replicas for heavy analytics queries on OLTP primary
- Apply LIMIT + cursor pagination for large result sets
- Set statement_timeout for user-facing queries
- Enable connection pooling (PgBouncer) for high-concurrency workloads

## Platform-Specific Capabilities

### PostgreSQL (Primary Stack)
- Window functions: `OVER (PARTITION BY ... ORDER BY ...)`
- Recursive CTEs: hierarchical data traversal
- JSON/JSONB: `@>`, `#>>`, `jsonb_path_query`
- Full-text: `to_tsvector`, `ts_rank`, GIN indexes
- Temporal: `timestamptz`, `AT TIME ZONE`, `generate_series` for gaps
- Extensions: `pg_stat_statements`, `pg_trgm`, `uuid-ossp`, `pgcrypto`

### Cloud Analytics Platforms
- **BigQuery**: Standard SQL, partitioned tables, clustering, `INFORMATION_SCHEMA`
- **Snowflake**: Zero-copy cloning, time-travel, micro-partitioning, tasks + streams
- **Redshift**: Distribution keys, sort keys, VACUUM + ANALYZE cadence
- **Databricks**: Delta Lake, `MERGE INTO`, streaming + batch unification

### Time-Series
- **TimescaleDB**: Hypertables, continuous aggregates, compression policies
- **InfluxDB**: Flux queries, bucket retention, downsampling tasks
- **Apache Druid**: Real-time ingestion, rollup, approximate aggregations (HLL, quantiles)

## Advanced SQL Patterns

### Window Functions
```sql
-- Running total + rank within partition
SELECT
    user_id,
    order_date,
    total,
    SUM(total) OVER (PARTITION BY user_id ORDER BY order_date) AS running_total,
    RANK() OVER (PARTITION BY user_id ORDER BY total DESC) AS rank_in_user
FROM orders;
```

### Recursive CTE (Hierarchical Data)
```sql
WITH RECURSIVE org_tree AS (
    -- Base case: root nodes
    SELECT id, name, parent_id, 0 AS depth
    FROM employees WHERE parent_id IS NULL
    UNION ALL
    -- Recursive case
    SELECT e.id, e.name, e.parent_id, ot.depth + 1
    FROM employees e
    JOIN org_tree ot ON e.parent_id = ot.id
)
SELECT * FROM org_tree ORDER BY depth, name;
```

### HTAP Pattern — Separate Read/Write Paths
```sql
-- Write path: OLTP primary (PostgreSQL)
INSERT INTO orders (user_id, total, created_at) VALUES ($1, $2, NOW());

-- Read path: replica or analytics DB
-- Use logical replication to BigQuery/Snowflake for heavy aggregations
SELECT DATE_TRUNC('month', created_at), SUM(total)
FROM orders
GROUP BY 1 ORDER BY 1;
-- Route this to read replica, not primary
```

### SCD Type 2 (Slowly Changing Dimensions)
```sql
-- Invalidate current record, insert new version
UPDATE dim_customers
SET valid_to = NOW(), is_current = FALSE
WHERE customer_id = $1 AND is_current = TRUE;

INSERT INTO dim_customers (customer_id, name, email, valid_from, valid_to, is_current)
VALUES ($1, $2, $3, NOW(), '9999-12-31', TRUE);
```

## Anti-Patterns

- Running heavy OLAP aggregations on OLTP primary — use read replica or separate analytics DB
- `SELECT *` on wide fact tables in analytics workloads — columns are stored separately in columnar DBs
- Non-partitioned tables for time-series data exceeding 1M rows — always partition by time
- Correlated subqueries in analytical queries — always transform to JOINs or window functions
- Implicit type casting in JOIN conditions — prevents index usage, causes full scans
- DDL inside transactions on BigQuery/Snowflake — not supported; manage schema changes separately

## Documentation Sources

- PostgreSQL docs: Query MCP context7 with library ID `/postgresql/postgresql`
- BigQuery: Query MCP context7 with library ID `/googleapis/google-cloud-bigquery`
- Snowflake SQL reference: `WebFetch` from Snowflake documentation
- TimescaleDB: Query MCP context7

## Reference Files

*(None yet — patterns are inline above. Add `reference/cloud-platform-sql.md` when cloud-specific patterns grow beyond this file.)*

## Related Skills

- `sql-optimization-patterns` — PostgreSQL OLTP query tuning, EXPLAIN analysis, N+1 fixes, cursor pagination
- `database-schema-designer` — Schema design, Flyway migrations, normalization, FK/index rules
- `vector-database` — pgvector, HNSW/IVFFlat, RAG pipelines
- `python-dev` — SQLAlchemy async, asyncpg, FastAPI integration
- `java-spring-api` — R2DBC reactive PostgreSQL
- `nestjs-api` — Prisma ORM, raw SQL via Prisma
