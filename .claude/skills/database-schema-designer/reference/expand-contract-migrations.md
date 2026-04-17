# Expand-Contract Migration Pattern

Zero-downtime schema migrations using the Expand-Contract strategy for PostgreSQL + Flyway (Java) and Prisma (NestJS).

---

## The 3 Phases

| Phase | What Happens | Code State | Safe to Deploy? |
|-------|-------------|------------|-----------------|
| **EXPAND** | Add new nullable column/table; write to BOTH old + new; read from OLD | Old + New code deployed | YES |
| **MIGRATE** | Backfill historical rows; switch reads to NEW column | New code reads new, old code ignores | YES |
| **CONTRACT** | Drop old column/constraint; clean up | New code only | YES (after N deploys) |

**Rule:** Never collapse phases into a single migration. Each phase must survive independently in production.

---

## PostgreSQL CONCURRENTLY Patterns

### CREATE INDEX CONCURRENTLY

Builds the index without holding a table-level lock — reads and writes continue uninterrupted during index creation.

```sql
-- Expand phase: add index on new column without blocking queries
CREATE INDEX CONCURRENTLY idx_users_email_v2 ON users(email_v2);
```

**Constraint:** Cannot run inside a transaction block. Flyway wraps migrations in transactions by default — disable this per-file:

```sql
-- flyway:executeInTransaction=false
CREATE INDEX CONCURRENTLY idx_users_email_v2 ON users(email_v2);
```

### DROP INDEX CONCURRENTLY

Safe to use during the contract phase — does not block reads or writes.

```sql
-- Contract phase: remove old index without locking
DROP INDEX CONCURRENTLY idx_users_email_old;
```

---

## Batched Backfill with SKIP LOCKED

Never backfill millions of rows in a single `UPDATE` — it holds a long-running lock and causes replication lag.

**Pattern:** run this statement repeatedly in a loop (application code or a migration job) until it returns 0 rows updated.

```sql
-- Batched backfill (run repeatedly until 0 rows updated)
UPDATE users
SET    new_email = old_email
WHERE  id IN (
  SELECT id FROM users
  WHERE  new_email IS NULL
  ORDER BY id
  LIMIT  1000
  FOR UPDATE SKIP LOCKED
);
```

**Why SKIP LOCKED:** rows locked by another transaction are skipped instead of waited on. This eliminates lock contention and allows concurrent reads to proceed at full speed during the backfill window. Each batch completes quickly, keeping lock duration under ~50ms per batch.

---

## Prisma Expand-Contract Workaround

**Problem:** Prisma generates `CREATE INDEX` statements and wraps `prisma migrate dev` in a transaction. `CREATE INDEX CONCURRENTLY` cannot run inside a transaction — Prisma will error.

**Solution:** Use `--create-only` to generate the SQL file without applying it, then edit the SQL manually before deploying.

```bash
# 1. Generate migration SQL without applying it
npx prisma migrate dev --create-only --name add_new_email_idx

# 2. Edit migrations/xxx_add_new_email_idx/migration.sql
# Change: CREATE INDEX ...
# To:     CREATE INDEX CONCURRENTLY ...

# 3. Apply manually (Prisma won't wrap in transaction)
npx prisma migrate deploy
```

**Warning:** Never use `prisma migrate dev` (without `--create-only`) for `CONCURRENTLY` operations — it runs inside a transaction and will fail with:

```
ERROR: CREATE INDEX CONCURRENTLY cannot run inside a transaction block
```

---

## Flyway Expand-Contract Example

Expand phase migration that adds a new column and a concurrent index, with transaction isolation disabled:

```sql
-- flyway:executeInTransaction=false
-- V2__expand_add_email_v2.sql

ALTER TABLE users ADD COLUMN email_v2 TEXT;
CREATE INDEX CONCURRENTLY idx_users_email_v2 ON users(email_v2);
```

Contract phase (separate migration file, separate deploy):

```sql
-- flyway:executeInTransaction=false
-- V4__contract_drop_email_old.sql

DROP INDEX CONCURRENTLY idx_users_email;
ALTER TABLE users DROP COLUMN email;
```

---

## Anti-Patterns

| Anti-pattern | Problem | Fix |
|-------------|---------|-----|
| Renaming a column in one migration | Running app reads old name → crashes | Expand-Contract: add new column, backfill, switch reads, drop old |
| `CREATE INDEX` without CONCURRENTLY in production | Table-level lock blocks all reads and writes | Always use `CREATE INDEX CONCURRENTLY` in production |
| Running CONTRACT phase in the same deploy as EXPAND | Old code still deployed reads the dropped column → 500 errors | Wait at least N deploys (all old instances drained) before contracting |
| Single-statement backfill on large table | Lock timeout, replication lag, OOM risk | Batch with `SKIP LOCKED` — 1000 rows per iteration |
