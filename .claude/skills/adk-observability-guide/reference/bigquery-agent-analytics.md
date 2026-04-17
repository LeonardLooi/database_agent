# BigQuery Agent Analytics Plugin

> **Opt-in (Tier 3).** Enable with `--bq-analytics` at scaffold time, or add manually to `app/agent.py`.

An optional plugin that logs structured agent events directly to BigQuery via the Storage Write API.

## Enabling

| Method | How |
|--------|-----|
| **At scaffold time** | `uvx agent-starter-pack create . --bq-analytics` |
| **Post-scaffold** | Add the plugin manually to `app/agent.py` (see ADK docs link below) |

Infrastructure (BigQuery dataset, GCS offloading) is provisioned automatically by Terraform when enabled at scaffold time.

## Key Features

- **Auto-schema upgrade** — new fields added without migration
- **GCS offloading** — multimodal content (images, audio) stored in GCS, not in BigQuery rows
- **OpenTelemetry span context** — distributed tracing linked to structured events
- **SQL-queryable event log** — every agent interaction queryable via standard SQL

## Tool Provenance Tracking

Every tool call is tagged with its origin:

| Provenance | Meaning |
|------------|---------|
| `LOCAL` | Tool defined in the agent's own codebase |
| `MCP` | Tool sourced from an MCP server |
| `SUB_AGENT` | Tool call delegated to a sub-agent |
| `A2A` | Tool call via Agent-to-Agent protocol |
| `TRANSFER_AGENT` | Control transferred to another agent |

## Use Cases

- Conversational analytics — session flows, user interaction patterns
- LLM-as-judge evals — structured data for evaluation pipelines
- Custom dashboards — Looker Studio integration over BigQuery
- Tool usage analysis — which tools are called, how often, from what provenance

For full schema, SQL query examples, and Looker Studio setup, fetch:
`https://google.github.io/adk-docs/integrations/bigquery-agent-analytics/index.md`
