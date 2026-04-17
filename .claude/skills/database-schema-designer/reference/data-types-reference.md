# Data Types Reference

Choose appropriate data types for each column to enforce correctness, optimize storage, and communicate intent.

---

## String Types

| Type | Use Case | Example |
|------|----------|---------|
| CHAR(n) | Fixed length | State codes, ISO country codes |
| VARCHAR(n) | Variable length | Names, emails, URLs |
| TEXT | Long content | Articles, descriptions, comments |

```sql
-- Good sizing examples
email VARCHAR(255)
phone VARCHAR(20)
country_code CHAR(2)
username VARCHAR(50)
bio TEXT
```

### String Sizing Guidelines

| Field | Recommended Size |
|-------|-----------------|
| Email | VARCHAR(255) |
| Username | VARCHAR(50) |
| First/Last name | VARCHAR(100) |
| Phone | VARCHAR(20) |
| URL | VARCHAR(2048) |
| Country code | CHAR(2) |
| Currency code | CHAR(3) |
| State/Province | VARCHAR(50) |
| Postal code | VARCHAR(20) |

**Rule:** Size VARCHAR to the realistic maximum for the field. Avoid VARCHAR(255) as a default -- it hides intent.

---

## Numeric Types

| Type | Range | Use Case |
|------|-------|----------|
| TINYINT | -128 to 127 | Age, status codes, flags |
| SMALLINT | -32K to 32K | Quantities, small counts |
| INT | -2.1B to 2.1B | IDs, counts, standard integers |
| BIGINT | Very large | Large IDs, timestamps, big counters |
| DECIMAL(p,s) | Exact precision | Money, financial calculations |
| FLOAT/DOUBLE | Approximate | Scientific data, coordinates |

```sql
-- ALWAYS use DECIMAL for money
price DECIMAL(10, 2)  -- Up to $99,999,999.99

-- NEVER use FLOAT for money
price FLOAT  -- Rounding errors!
```

### Numeric Guidelines

| Data | Type | Example |
|------|------|---------|
| Money/currency | DECIMAL(10,2) | `price DECIMAL(10,2)` |
| Percentage | DECIMAL(5,2) | `discount DECIMAL(5,2)` |
| Latitude/Longitude | DECIMAL(9,6) | `lat DECIMAL(9,6)` |
| Auto-increment ID | INT or BIGINT | `id BIGINT AUTO_INCREMENT` |
| Boolean flag | BOOLEAN or TINYINT(1) | `is_active BOOLEAN` |
| Quantity | INT or SMALLINT | `quantity INT` |

---

## Date/Time Types

```sql
DATE        -- 2025-10-31 (date only)
TIME        -- 14:30:00 (time only)
DATETIME    -- 2025-10-31 14:30:00 (no timezone)
TIMESTAMP   -- Auto timezone conversion (store UTC)
```

### Best Practices for Dates

```sql
-- Always store in UTC
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
```

| Scenario | Type | Reason |
|----------|------|--------|
| Record creation time | TIMESTAMP | Auto UTC conversion |
| User's birthday | DATE | No time component needed |
| Scheduled event | TIMESTAMP | Need timezone awareness |
| Duration | INT (seconds) | Simple math operations |
| Historical date | DATE | No timezone ambiguity |

**Rule:** Store all timestamps in UTC. Convert to local timezone in the application layer.

---

## Boolean Types

```sql
-- PostgreSQL
is_active BOOLEAN DEFAULT TRUE

-- MySQL
is_active TINYINT(1) DEFAULT 1
```

**Rule:** Use the native BOOLEAN type when available. In MySQL, TINYINT(1) is the conventional equivalent.

---

## JSON Types

```sql
-- PostgreSQL JSONB (preferred - indexed, efficient)
metadata JSONB DEFAULT '{}'::jsonb

-- MySQL JSON
attributes JSON
```

### When to Use JSON

| Use JSON | Avoid JSON |
|----------|------------|
| Flexible attributes | Core business data |
| User preferences | Frequently queried fields |
| API response caching | Fields needing constraints |
| Schema-less metadata | Relational data |

**Rule:** Use JSON for truly flexible data. If you query a JSON field frequently, extract it to a proper column.

---

## Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| VARCHAR(255) everywhere | Wastes storage, hides intent | Size appropriately per field |
| FLOAT for money | Rounding errors | DECIMAL(10,2) |
| Storing dates as strings | Cannot compare/sort properly | DATE, TIMESTAMP types |
| INT for boolean | Unclear intent | BOOLEAN or TINYINT(1) |
| TEXT for short strings | No length validation | VARCHAR(n) with proper size |
| Storing IP as VARCHAR | Wastes space, slow comparison | INET (PostgreSQL) or INT |
