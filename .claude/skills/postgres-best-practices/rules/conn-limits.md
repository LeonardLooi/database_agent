---
title: Set Appropriate Connection Limits
impact: CRITICAL
impactDescription: Prevent database crashes and memory exhaustion
tags: connections, max-connections, limits, stability
---

## Set Appropriate Connection Limits

Too many connections exhaust memory and degrade performance. Set limits based on available resources.

**Incorrect (unlimited or excessive connections):**

```sql
-- Default max_connections = 100, but often increased blindly
show max_connections;  -- 500 (way too high for 4GB RAM)

-- Each connection uses 1-3MB RAM
-- 500 connections * 2MB = 1GB just for connections!
-- Out of memory errors under load
```

**Correct (calculate based on resources):**

```sql
-- Formula: max_connections = (RAM in MB / 5MB per connection) - reserved
-- For 4GB RAM: (4096 / 5) - 10 = ~800 theoretical max
-- But practically, 100-200 is better for query performance

-- Recommended settings for 4GB RAM
alter system set max_connections = 100;

-- Also set work_mem appropriately
-- work_mem * max_connections should not exceed 25% of RAM
alter system set work_mem = '8MB';  -- 8MB * 100 = 800MB max
```

Monitor connection usage:

```sql
select count(*), state from pg_stat_activity group by state;
```

### Full Configuration Template

```sql
-- PostgreSQL connection and timeout configuration (ALTER SYSTEM = persistent, survives restart)
-- Run as superuser, then reload: SELECT pg_reload_conf();

-- Connection limits
ALTER SYSTEM SET max_connections = '100';  -- default 100; use PgBouncer for >100 app connections
ALTER SYSTEM SET superuser_reserved_connections = '3';  -- reserve for emergency admin access

-- Memory per connection (set low — total = max_connections × work_mem for sort operations)
ALTER SYSTEM SET work_mem = '4MB';  -- default 4MB; tune per query, not globally
ALTER SYSTEM SET maintenance_work_mem = '64MB';  -- for VACUUM, CREATE INDEX

-- Timeout settings (prevent runaway queries and idle transactions)
ALTER SYSTEM SET statement_timeout = '30s';  -- kill queries running longer than 30s
ALTER SYSTEM SET lock_timeout = '10s';  -- fail fast if waiting for lock > 10s
ALTER SYSTEM SET idle_in_transaction_session_timeout = '60s';  -- kill idle transactions

-- Apply without restart:
SELECT pg_reload_conf();

-- Verify applied:
SHOW max_connections;
SHOW statement_timeout;
SHOW lock_timeout;
```

Reference: [Database Connections](https://supabase.com/docs/guides/platform/performance#connection-management)
