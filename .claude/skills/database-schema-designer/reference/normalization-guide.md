# Normalization Guide

Apply normal forms to eliminate data redundancy and ensure data integrity in SQL databases.

---

## Normal Forms Summary

| Form | Rule | Violation Example |
|------|------|-------------------|
| **1NF** | Atomic values, no repeating groups | `product_ids = '1,2,3'` |
| **2NF** | 1NF + no partial dependencies | customer_name in order_items |
| **3NF** | 2NF + no transitive dependencies | country derived from postal_code |

---

## 1st Normal Form (1NF)

Every column must contain atomic (single) values. No repeating groups or arrays stored in a single column.

```sql
-- BAD: Multiple values in column
CREATE TABLE orders (
  id INT PRIMARY KEY,
  product_ids VARCHAR(255)  -- '101,102,103'
);

-- GOOD: Separate table for items
CREATE TABLE orders (
  id INT PRIMARY KEY,
  customer_id INT
);

CREATE TABLE order_items (
  id INT PRIMARY KEY,
  order_id INT REFERENCES orders(id),
  product_id INT
);
```

**Key test:** Can every cell in the table hold only one value? If not, split into a separate table.

---

## 2nd Normal Form (2NF)

Every non-key column must depend on the entire primary key, not just part of it. This only applies to tables with composite primary keys.

```sql
-- BAD: customer_name depends only on customer_id, not on (order_id, product_id)
CREATE TABLE order_items (
  order_id INT,
  product_id INT,
  customer_name VARCHAR(100),  -- Partial dependency!
  PRIMARY KEY (order_id, product_id)
);

-- GOOD: Customer data in separate table
CREATE TABLE customers (
  id INT PRIMARY KEY,
  name VARCHAR(100)
);
```

**Key test:** For composite keys, does every non-key column depend on ALL parts of the key? If not, extract to a separate table.

---

## 3rd Normal Form (3NF)

No non-key column should depend on another non-key column. Remove transitive dependencies.

```sql
-- BAD: country depends on postal_code, not directly on id
CREATE TABLE customers (
  id INT PRIMARY KEY,
  postal_code VARCHAR(10),
  country VARCHAR(50)  -- Transitive dependency!
);

-- GOOD: Separate postal_codes table
CREATE TABLE postal_codes (
  code VARCHAR(10) PRIMARY KEY,
  country VARCHAR(50)
);
```

**Key test:** Does any non-key column determine another non-key column? If yes, extract the dependency into its own table.

---

## When to Denormalize

Denormalization intentionally introduces redundancy to improve read performance. Apply selectively after measuring actual query bottlenecks.

| Scenario | Denormalization Strategy |
|----------|-------------------------|
| Read-heavy reporting | Pre-calculated aggregates |
| Expensive JOINs | Cached derived columns |
| Analytics dashboards | Materialized views |
| High-traffic reads | Denormalized read models |

```sql
-- Denormalized for performance
CREATE TABLE orders (
  id INT PRIMARY KEY,
  customer_id INT,
  total_amount DECIMAL(10,2),  -- Calculated from order_items
  item_count INT               -- Calculated from order_items
);
```

### Denormalization Rules

1. **Normalize first** -- always start at 3NF
2. **Measure before denormalizing** -- profile actual slow queries
3. **Document the trade-off** -- note which normal form is violated and why
4. **Keep source of truth normalized** -- denormalized copies are caches
5. **Plan for consistency** -- triggers, application logic, or eventual consistency

---

## Decision Guide: Normalization Level

| Workload Type | Recommended Level | Reason |
|---------------|-------------------|--------|
| OLTP (transactions) | 3NF | Write integrity critical |
| OLAP (analytics) | Denormalized / star schema | Read performance critical |
| Mixed workload | 3NF + materialized views | Balance both needs |
| Microservice local DB | 3NF within service boundary | Keep service data clean |
