# Tactical Design Reference

## Aggregate Design

### Principles

1. **Protect business invariants** — an aggregate enforces rules that must always be true
2. **Small aggregates** — prefer 1-3 entities per aggregate. Large aggregates cause contention
3. **Reference by ID** — aggregates reference other aggregates by identity, never by direct object reference
4. **Single transaction** — one aggregate = one transaction boundary. Never modify two aggregates in one transaction
5. **Eventual consistency between aggregates** — use domain events to synchronize

### Aggregate Sizing Checklist

- [ ] Can this aggregate be loaded in a single DB query?
- [ ] Does it fit in memory comfortably?
- [ ] Will concurrent users contend on the same aggregate?
- [ ] If I split this, do any invariants break?

If contention is high or memory is large → split into smaller aggregates connected by events.

### Aggregate Design Template

```markdown
## Aggregate: [Name]

**Root Entity:** [AggregateRoot]
**Invariants:**
1. [Business rule that must always hold]
2. [Another invariant]

**Entities:**
- [Entity]: [purpose, lifecycle]

**Value Objects:**
- [VO]: [what it represents, equality rule]

**Commands (state changes):**
- [CommandName]: [what it does, preconditions, postconditions]

**Events Emitted:**
- [EventName]: [when emitted, what data it carries]

**Repository Interface:**
- findById(id): [AggregateRoot]
- save(aggregate): void
```

### Common Aggregate Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| God aggregate (20+ entities) | Memory, contention, complexity | Split by invariant boundaries |
| Aggregate references aggregate by object | Tight coupling, loading cascades | Reference by ID only |
| Multi-aggregate transaction | Distributed lock, scalability killer | Use domain events + eventual consistency |
| Anemic aggregate (no behavior) | Logic leaks into services | Move business rules INTO the aggregate |
| Entity used as value object | Unnecessary identity tracking | If equality is by value, make it a VO |

## Entity Design

- Has unique identity that persists across state changes
- Identity is immutable once assigned
- Equality based on identity, NOT attribute values
- Contains behavior — not just getters/setters

```
Entity Checklist:
- [ ] Has a unique ID (UUID, natural key, or sequence)
- [ ] Identity never changes
- [ ] Has behavior methods (not just data)
- [ ] State changes go through methods that enforce rules
```

## Value Object Design

- No identity — equality based on ALL attributes
- Immutable — once created, never changes
- Self-validating — constructor enforces constraints
- Replaceable — swap the whole object, don't mutate

Good value objects: Money, Address, DateRange, Email, PhoneNumber, Coordinates, Quantity

```
Value Object Checklist:
- [ ] No ID field
- [ ] All fields final/readonly
- [ ] equals() compares all fields
- [ ] Constructor validates invariants
- [ ] No setters — create new instance instead
```

## Domain Events

### Event Design Principles

1. **Past tense naming**: `OrderPlaced`, `PaymentReceived`, `UserRegistered`
2. **Carry enough data**: Consumer should NOT need to call back to the producer
3. **Immutable**: Once emitted, an event never changes
4. **Schema versioned**: Events evolve — use versioning from day one
5. **Idempotent consumers**: Handlers must tolerate duplicate delivery

### Event Schema Template

```markdown
## Event: [PastTenseVerbNoun]

**Emitted by:** [Aggregate]
**Trigger:** [What state change causes this]
**Schema version:** v1

**Payload:**
| Field | Type | Description |
|-------|------|-------------|
| eventId | UUID | Unique event identifier |
| occurredAt | DateTime | When the event happened |
| aggregateId | UUID | ID of the source aggregate |
| [field] | [type] | [description] |

**Consumers:**
- [Context/Service]: [what it does with this event]
```

### Event Versioning Strategy

- **Additive changes** (new optional field): Same schema version, backward compatible
- **Breaking changes** (remove/rename field): New schema version, run both in parallel
- **Event upcasting**: Transform old event format to new on read

## Domain Services

Use a domain service when:

- Logic doesn't naturally belong to any single entity or value object
- Operation involves multiple aggregates (coordination, not transaction)
- External system interaction is needed to make a domain decision

Do NOT use a domain service when:

- Logic belongs on an entity (push it into the entity)
- It's purely technical (that's an application or infrastructure service)

```
Domain Service Checklist:
- [ ] Stateless — no instance variables
- [ ] Named using ubiquitous language
- [ ] Operates on domain objects, not raw data
- [ ] Does NOT handle persistence (that's the repository)
```

## Saga / Process Manager

For workflows spanning multiple aggregates or bounded contexts:

### Choreography (event-driven, no central coordinator)

```
Aggregate A emits Event1
    → Aggregate B listens, does work, emits Event2
        → Aggregate C listens, does work, emits Event3
```

**Use when:** Simple flows (2-3 steps), loose coupling preferred
**Risk:** Hard to understand the full flow, no single place shows the sequence

### Orchestration (central process manager)

```
Saga receives trigger
    → Commands Aggregate A → waits for response
    → Commands Aggregate B → waits for response
    → Commands Aggregate C → completes
```

**Use when:** Complex flows (4+ steps), compensation logic needed, visibility required
**Risk:** Central coordinator becomes a bottleneck or single point of failure

### Compensation Pattern

Every saga step needs a compensating action for failure:

```markdown
| Step | Action | Compensation |
|------|--------|-------------|
| 1 | Reserve inventory | Release inventory |
| 2 | Charge payment | Refund payment |
| 3 | Create shipment | Cancel shipment |
```

## CQRS Decision Framework

Apply CQRS (separate read/write models) when:

- [ ] Read and write patterns are significantly different
- [ ] Read model needs denormalized views for performance
- [ ] Multiple consumers need different projections of the same data
- [ ] Write model is event-sourced

Do NOT apply CQRS when:

- Simple CRUD with no complex queries
- Team is small and complexity budget is limited
- Read and write models are nearly identical
