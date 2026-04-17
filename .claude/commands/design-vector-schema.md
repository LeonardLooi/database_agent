---
description: Design a pgvector migration SQL file. Captures model + dimension + distance metric + row count → generates reversible Flyway/Alembic migration with correct index type, metadata columns, and null guards.
argument-hint: "[table name] [embedding model] [row count estimate]"
allowed-tools: Bash, Read, Write, Edit
disable-model-invocation: true
---

# Design Vector Schema

Generate a production-ready pgvector migration for the following:

**Input:** $ARGUMENTS

## Steps

1. **Load the `vector-database` skill** — read `SKILL.md` and `references/pgvector-migration-template.md` for templates and operator-index alignment rules.

2. **Gather requirements** — Extract from `$ARGUMENTS` or ask:
   - Table name (existing or new)
   - Embedding model (from skill's model table — `text-embedding-3-small`, `text-embedding-3-large`, `embed-english-v3.0`, `voyage-3-large`, `nomic-embed-text`)
   - Estimated row count (determines HNSW vs IVFFlat)
   - Distance metric (cosine / L2 / inner product)
   - Migration format (Flyway `V{N}__*.sql` or Alembic `{revision}_.py`)

3. **Select index type** based on row count:
   - < 100K rows: IVFFlat (with ANALYZE reminder)
   - ≥ 100K rows: HNSW
   - Always default to HNSW if count is unknown

4. **Generate migration file** with:
   - `CREATE EXTENSION IF NOT EXISTS vector;` at top of `up()`
   - `vector({dims})` column — dimension from model table
   - `embedding_model varchar(100) DEFAULT '{model}'`
   - `embedded_at timestamptz`
   - Correct index with matching ops class
   - Null guard partial index (`WHERE embedding IS NOT NULL`) for tables > 50K rows
   - Reversible `down()` section
   - Comment block: model, dims, distance metric, index params reasoning

5. **Run `pgvector-schema-reviewer` agent** on the generated file before presenting to user.

6. **Save file** to `src/main/resources/db/migration/` (Flyway) or `alembic/versions/` (Alembic) depending on project structure. If neither exists, save to current directory with correct naming convention.

7. **Report** what was generated and any reviewer findings.

$ARGUMENTS
