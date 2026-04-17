---
description: Design a database schema with ERD, migrations, and indexes for a given domain
argument-hint: "[domain or requirements]"
allowed-tools: Bash, Read, Write, Edit
disable-model-invocation: true
---

# Design Database Schema

Design a complete database schema for the following domain:

**Domain / Requirements:** $ARGUMENTS

## Steps
1. Identify the core entities and their relationships
2. Draw an ERD in Mermaid syntax
3. Write Flyway migration SQL files (`V1__*.sql`, `V2__*.sql`, etc.)
4. Include proper indexes for expected query patterns
5. Add `updated_at` trigger function
6. If Firestore is relevant, provide the collection/document structure
7. Provide Firestore security rules if applicable
8. Summarize the design decisions

Use the database-schema-designer skill for conventions and templates.
Save output files to a `docs/database/` directory.
