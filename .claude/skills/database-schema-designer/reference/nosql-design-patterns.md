# NoSQL Design Patterns

Design effective document schemas for MongoDB, Firestore, and other NoSQL databases. Focus on access patterns over normalization.

---

## Embedding vs Referencing

The fundamental design decision in document databases: store related data together (embed) or separately (reference).

| Factor | Embed | Reference |
|--------|-------|-----------|
| Access pattern | Read together | Read separately |
| Relationship | 1:few | 1:many or many:many |
| Document size | Small, bounded | Approaching size limits |
| Update frequency | Rarely changes | Frequently updated |
| Data duplication | Acceptable | Must avoid |

### Decision Guide

Embed when:
- Data is always read together
- Child data does not exist without the parent
- The embedded array is bounded (will not grow indefinitely)
- Child data rarely changes independently

Reference when:
- Data is read independently
- Many-to-many relationships exist
- The referenced data changes frequently
- The array of references could grow unbounded

---

## MongoDB Patterns

### Embedded Document

Store related data inside the parent document for single-query reads.

```json
{
  "_id": "order_123",
  "customer": {
    "id": "cust_456",
    "name": "Jane Smith",
    "email": "jane@example.com"
  },
  "items": [
    { "product_id": "prod_789", "quantity": 2, "price": 29.99 }
  ],
  "total": 109.97
}
```

**Use for:** Orders with items, blog posts with comments (bounded), user profiles with addresses.

### Referenced Document

Store related data in separate collections, linked by ID.

```json
// orders collection
{
  "_id": "order_123",
  "customer_id": "cust_456",
  "item_ids": ["item_1", "item_2"],
  "total": 109.97
}

// customers collection
{
  "_id": "cust_456",
  "name": "Jane Smith",
  "email": "jane@example.com"
}
```

**Use for:** Shared data (customers across orders), large related datasets, independently accessed entities.

### Hybrid Pattern

Embed frequently read fields, reference the full document.

```json
{
  "_id": "order_123",
  "customer": {
    "id": "cust_456",
    "name": "Jane Smith"
  },
  "items": [
    { "product_id": "prod_789", "name": "Widget", "quantity": 2, "price": 29.99 }
  ]
}
```

Embed the customer name and product name for display, but reference the full customer/product document for details.

---

## MongoDB Indexes

```javascript
// Single field
db.users.createIndex({ email: 1 }, { unique: true });

// Composite
db.orders.createIndex({ customer_id: 1, created_at: -1 });

// Text search
db.articles.createIndex({ title: "text", content: "text" });

// Geospatial
db.stores.createIndex({ location: "2dsphere" });

// TTL (auto-expire documents)
db.sessions.createIndex({ "lastAccess": 1 }, { expireAfterSeconds: 3600 });
```

---

## Firestore Design Patterns

### Collection/Document Hierarchy

```
users/
  {userId}/
    name: "Jane Smith"
    email: "jane@example.com"
    orders/              <-- subcollection
      {orderId}/
        total: 109.97
        items: [...]     <-- embedded array
```

### Firestore Rules

1. **Denormalize for reads** -- duplicate data to avoid multiple reads
2. **Keep documents small** -- under 1MB, ideally under 10KB
3. **Use subcollections for large lists** -- instead of arrays in a document
4. **Flatten for queries** -- Firestore cannot query across subcollections (use collection group queries)

### Denormalization Example

```json
// users/{userId}
{
  "name": "Jane Smith",
  "orderCount": 5,
  "lastOrderDate": "2025-01-15"
}

// orders/{orderId}
{
  "userId": "user_123",
  "userName": "Jane Smith",
  "items": [
    { "productId": "prod_789", "productName": "Widget", "quantity": 2 }
  ]
}
```

Duplicate `userName` in orders and `orderCount` in users to avoid extra reads. Update duplicated data with Cloud Functions or batch writes.

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Unbounded arrays | Document grows past size limit | Use subcollection or reference |
| Deep nesting | Hard to query and update | Flatten to 2-3 levels max |
| No indexes | Full collection scans | Index all query patterns |
| Over-embedding | Wasteful updates | Reference frequently-changing data |
| Treating NoSQL like SQL | Complex joins, poor performance | Design for access patterns |

---

## Migration: SQL to NoSQL

| SQL Concept | NoSQL Equivalent |
|-------------|-----------------|
| Table | Collection |
| Row | Document |
| Column | Field |
| JOIN | Embedded document or application-side join |
| Foreign key | Document reference (no enforcement) |
| Transaction | Multi-document transaction (limited) |
| Schema | Schema validation rules (optional) |
