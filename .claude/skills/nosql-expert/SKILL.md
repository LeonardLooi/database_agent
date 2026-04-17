---
name: nosql-expert
description: "Expert guidance for distributed NoSQL databases (Cassandra, DynamoDB, ScyllaDB). Covers query-first modeling, partition key design, hot partition prevention, single-table design, and BASE vs ACID tradeoffs. Triggers on: 'Cassandra', 'DynamoDB', 'NoSQL', 'partition key', 'hot partition', 'single-table design', 'GSI', 'LSI', 'WCU', 'RCU', 'ScyllaDB'."
argument-hint: "[entity, access pattern, or problem description]"
allowed-tools: Read
context: fork
metadata:
  triggers: Cassandra, DynamoDB, ScyllaDB, NoSQL, partition key, hot partition, single-table design, GSI, LSI, WCU, RCU, ALLOW FILTERING, clustering key, adjacency list, BASE consistency, eventual consistency, distributed database
  related-skills: database-schema-designer, sql-pro, architecture-design
  domain: infrastructure
  role: specialist
  scope: design
  output-format: document
last-reviewed: "2026-03-15"
---

## Iron Law

NEVER DESIGN A NOSQL SCHEMA WITHOUT LISTING ALL ACCESS PATTERNS FIRST — A TABLE DESIGNED FOR THE WRONG QUERIES REQUIRES A FULL MIGRATION

---

## When to Use This Skill

Load this skill when:
- Designing or reviewing a Cassandra, ScyllaDB, or DynamoDB schema
- Evaluating partition key choices or clustering column order
- Diagnosing hot partitions, Scan operations, or ALLOW FILTERING usage
- Deciding between single-table design and multi-table design in DynamoDB
- Modeling access patterns for a new feature on a distributed NoSQL store
- Migrating a relational model to a NoSQL model

---

## The Mental Shift: SQL vs Distributed NoSQL

| Feature | SQL (Relational) | Distributed NoSQL (Cassandra/DynamoDB) |
|---------|-----------------|---------------------------------------|
| Data modeling | Model Entities + Relationships | Model Queries (Access Patterns) |
| Joins | CPU-intensive, resolved at read time | Pre-computed (denormalized) at write time |
| Storage cost | Expensive — minimize duplication | Cheap — duplicate data for read speed |
| Consistency | ACID (Strong) | BASE (Eventual) / Tunable |
| Scalability | Vertical (bigger machine) | Horizontal (more nodes/shards) |
| Schema changes | ALTER TABLE, migrations | Often requires new table or full migration |
| Aggregates | COUNT, SUM, GROUP BY | Pre-calculate in separate counter tables |

**The golden rule:** In relational design, you model entities. In distributed NoSQL, you model the queries your application will execute.

---

## Core Design Patterns

### Pattern 1: Query-First Modeling

Before touching a schema tool, list every access pattern:

```
Access Patterns:
1. Get user by user_id
2. Get all orders for a user, sorted by created_at DESC
3. Get all orders in status PENDING for a given tenant
4. Get order by order_id
```

Each row in that list becomes either a primary key structure or an index. If a pattern has no corresponding key or index, it cannot be served efficiently — fix the schema before writing code.

### Pattern 2: Partition Key Design for Even Distribution

The partition key determines which node holds the data. Bad cardinality causes hot partitions.

```
-- BAD: status has 3-5 values — most traffic lands on one partition
PRIMARY KEY (status, created_at)

-- GOOD: user_id has millions of unique values — traffic spreads evenly
PRIMARY KEY (user_id, created_at)

-- GOOD: bucket sharding when one natural key is too large
-- Split USER#123 data across date buckets
PRIMARY KEY ((user_id, bucket), created_at)  -- bucket = YYYY-MM
```

Cardinality target: the partition key should have enough unique values that no single value represents more than 1-2% of total traffic.

### Pattern 3: Clustering Column Ordering for Range Queries

Clustering columns define the sort order within a partition. Design them to match your range query direction.

```cql
-- Cassandra: retrieve a user's messages, newest first
CREATE TABLE messages_by_user (
    user_id     UUID,
    sent_at     TIMESTAMP,
    message_id  UUID,
    body        TEXT,
    PRIMARY KEY ((user_id), sent_at, message_id)
) WITH CLUSTERING ORDER BY (sent_at DESC, message_id ASC);

-- Query maps directly to the key structure — no ALLOW FILTERING needed
SELECT * FROM messages_by_user
WHERE user_id = ? AND sent_at > ?
LIMIT 20;
```

### Pattern 4: Denormalization — Duplicate for Read Speed

In distributed NoSQL, writes are cheap. Storage is cheap. Joins are impossible at scale. Duplicate data across tables so every read is a single-partition lookup.

```
-- Relational: one Author table, one Book table, JOIN at read time
-- Distributed NoSQL: store author data inside each book row

-- Table 1: books_by_author — primary lookup path
books_by_author: PK=(author_id), CK=(published_at, book_id)
  -> stores: title, genre, author_name, author_bio_short

-- Table 2: books_by_genre — secondary lookup path
books_by_genre: PK=(genre), CK=(published_at, book_id)
  -> stores: title, author_id, author_name (duplicated)
```

Rule: when author_name changes, update both tables in the same application transaction. Accept that brief inconsistency is tolerable (BASE).

### Pattern 5: Adjacency List (DynamoDB Single-Table Design)

Store multiple entity types and their relationships in one DynamoDB table using composite key prefixes. This minimizes WCU/RCU consumption and enables single-request relationship fetches.

```
Table: AppData
PK (partition key)    SK (sort key)         Attributes
------------------    ---------------       --------------------
USER#123              USER#123              name, email, created_at
USER#123              ORDER#2024-001        total, status, items
USER#123              ORDER#2024-002        total, status, items
ORDER#2024-001        ORDER#2024-001        total, status, user_id
PRODUCT#SKU-99        PRODUCT#SKU-99        name, price, stock

-- Fetch user + all their orders in ONE query (same partition)
Query: PK = "USER#123", SK begins_with "ORDER#"
```

---

## Apache Cassandra / ScyllaDB Specifics

### Primary Key Structure

```cql
PRIMARY KEY ((partition_key_columns), clustering_columns)
--           ^--- always required      ^--- optional, define sort order
```

- The partition key routes data to a node. Can be composite: `((col1, col2), ...)`.
- Clustering columns define row ordering within a partition.

### Write Path: Why Writes Are Cheap

Cassandra uses an LSM (Log-Structured Merge) tree. Writes are sequential appends to a commit log and memtable — no random I/O. This makes write-heavy workloads (IoT, event streams, time-series) natural fits.

### Tombstones: Deletes Are Not Free

Deletes write a tombstone marker. Tombstones accumulate until compaction. High-velocity delete patterns (e.g., deleting individual items from a feed) cause tombstone buildup that degrades read performance.

Alternatives:
- Use TTL (`WITH TTL 86400`) for time-bounded data — Cassandra expires rows without tombstones
- Model deletes as status updates (`status = 'deleted'`) instead of physical deletes
- Use a separate "archived" table and write there instead of deleting from the primary table

### ALLOW FILTERING: Always a Red Flag

```cql
-- This compiles but scans every partition in the cluster
SELECT * FROM orders WHERE status = 'PENDING' ALLOW FILTERING;

-- Fix: create a table keyed by the query pattern
CREATE TABLE orders_by_status (
    status      TEXT,
    created_at  TIMESTAMP,
    order_id    UUID,
    PRIMARY KEY ((status), created_at, order_id)
);
```

If you see `ALLOW FILTERING` in production queries, the schema is wrong for that access pattern.

### No Joins, No Aggregates

```cql
-- FORBIDDEN in Cassandra at scale:
SELECT COUNT(*) FROM large_table;   -- full cluster scan
SELECT * FROM a JOIN b ON ...;      -- not supported

-- CORRECT: pre-compute counters in a dedicated counter table
CREATE TABLE order_counts_by_user (
    user_id   UUID PRIMARY KEY,
    total     COUNTER
);
UPDATE order_counts_by_user SET total = total + 1 WHERE user_id = ?;
```

---

## AWS DynamoDB Specifics

### Capacity Modes

| Mode | When to Use | Cost Model |
|------|-------------|------------|
| On-Demand | Unpredictable or spiky traffic | Pay per request (WCU/RCU consumed) |
| Provisioned | Steady, predictable traffic | Pay per provisioned WCU/RCU (cheaper at scale) |

Single-table design reduces the number of WCU/RCU consumed because multiple entity types share one table — fewer round trips per request.

### GSI vs LSI

**GSI (Global Secondary Index):**
- Defines a completely different partition key — creates an alternative view of the data
- Eventually consistent reads (can request strong consistency at 2x cost)
- Can be added after table creation
- Limit: 20 per table

**LSI (Local Secondary Index):**
- Same partition key as the base table, different sort key
- Enables additional range queries within a partition
- MUST be defined at table creation — cannot add later
- Strongly consistent reads available at no extra cost
- Limit: 5 per table, shares partition storage (10 GB per partition key)

```
-- Example: orders table
Base table:   PK=user_id, SK=order_id          -- get order by id
GSI-1:        PK=user_id, SK=created_at        -- get user's orders by date
GSI-2:        PK=status,  SK=created_at        -- ops dashboard: pending orders by date
LSI-1:        PK=user_id, SK=total             -- get user's orders by value (within partition)
```

### TTL for Automatic Expiry

DynamoDB TTL deletes expired items without consuming WCUs and without producing Cassandra-style tombstones.

```
-- Set TTL attribute on item (epoch timestamp)
expires_at: 1767225600   -- items deleted automatically after this time

-- Enable TTL on the table (attribute name must match)
aws dynamodb update-time-to-live \
  --table-name Sessions \
  --time-to-live-specification "Enabled=true, AttributeName=expires_at"
```

Use TTL for: sessions, OTP codes, cache entries, soft-deleted records.

---

## Expert Checklist (Before Finalizing Schema)

Run through every item before handing off a schema for review or implementation.

- [ ] **Access Pattern Coverage:** Every query pattern maps to a table, GSI, or LSI. No pattern requires ALLOW FILTERING or a Scan.
- [ ] **Cardinality Check:** The partition key has enough unique values that traffic is spread evenly across nodes/shards. No single value represents > 1-2% of total traffic.
- [ ] **Partition Size Check:** No single partition exceeds 10 GB (Cassandra) or 10 GB (DynamoDB LSI limit). If at risk, add a shard suffix: `USER#123#2024-01`.
- [ ] **Hot Key Risk:** Time-based or status-based partition keys are evaluated for hot key risk. Mitigation (bucket sharding, write spreading) is documented.
- [ ] **Tombstone Risk (Cassandra):** High-velocity delete patterns are replaced with TTL or status-update modeling.
- [ ] **Consistency Requirement:** The application's consistency tolerance is confirmed. If strong consistency is required everywhere, evaluate whether Cassandra or DynamoDB (without strong-read overhead) is the right tool.
- [ ] **Counter Tables:** Any aggregate (count, sum) has a dedicated counter table — never computed with SELECT COUNT(*).
- [ ] **Index Strategy (DynamoDB):** LSIs are confirmed at table creation (cannot be added later). GSIs are evaluated for WCU/RCU overhead.
- [ ] **Denormalization Documented:** Every duplicated field has a documented update strategy — which code path updates all copies.
- [ ] **TTL Strategy:** Time-bounded data uses TTL rather than application-level deletes.

---

## Common Anti-Patterns

### Scatter-Gather (Scan)
Querying all partitions to find matching items — equivalent to a full table scan.
```
-- DynamoDB: never do this in production
aws dynamodb scan --table-name Orders --filter-expression "status = :s"

-- Fix: add a GSI with status as partition key
```

### Hot Keys
All traffic for a time period or popular value routes to one partition.
```
-- BAD: day_of_week has 7 values — Monday gets crushed
PRIMARY KEY ((day_of_week), event_time, event_id)

-- GOOD: shard by (user_id % N) or use a high-cardinality natural key
PRIMARY KEY ((user_id), event_time, event_id)
```

### Relational Modeling in a NoSQL Store
Creating normalized entity tables (Users, Orders, Products) and then trying to join them at the application layer.
```
-- This pattern reconstructs relational joins in application code:
users = cassandra.execute("SELECT * FROM users WHERE id = ?")
orders = cassandra.execute("SELECT * FROM orders WHERE user_id = ?")
result = merge(users, orders)  # application-side join — latency doubles, errors multiply

-- Fix: denormalize. Store the user fields you need inside the orders table.
```

### Unbounded Partition Growth
Storing all records for a high-traffic entity under one partition key without time-bucketing.
```
-- BAD: all events for a popular user in one partition — grows without bound
PRIMARY KEY ((user_id), event_time, event_id)

-- GOOD: bucket by month — each partition stays bounded
PRIMARY KEY ((user_id, month), event_time, event_id)
-- month = '2024-03'
```

### Using ALLOW FILTERING as a Workaround
Silencing a Cassandra query error with ALLOW FILTERING instead of fixing the schema. See the Cassandra Specifics section above.
