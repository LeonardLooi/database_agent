---
name: adk-observability-guide
description: "ADK observability, Cloud Trace, prompt logging, agent analytics, BigQuery agent logs, ADK monitoring, ADK telemetry. Use when configuring tracing, logging, or analytics for ADK agents, debugging production agent behavior, or setting up monitoring for a deployed agent."
allowed-tools: Bash, Read, Write, Edit, WebFetch
metadata:
  triggers: ADK observability, Cloud Trace, prompt logging, agent analytics, BigQuery agent logs, ADK monitoring, ADK telemetry
  related-skills: google-adk, agentic-ai-dev, python-dev
  domain: backend
  role: specialist
  scope: observability
  output-format: code
last-reviewed: "2026-03-15"
---

# ADK Observability Guide

## Iron Law

**NEVER ship a production ADK agent without Cloud Trace enabled. Set `otel_to_cloud=True` in the FastAPI app and `LOGS_BUCKET_NAME` env var before any production deployment.**

## Reference Files

| File | Contents |
|------|----------|
| `reference/cloud-trace-and-logging.md` | Cloud Trace setup, prompt-response logging infrastructure, environment variables, enabling/disabling locally, verification commands |
| `reference/bigquery-agent-analytics.md` | BigQuery Agent Analytics plugin — enabling, key features, tool provenance tracking |
| `reference/slo-alerting.md` | SLO-based burn-rate alerting (vs threshold alerting), multi-window pattern, error budget tracking, PromQL examples for availability/latency/safety SLOs | Setting up production alerts for agentic AI services |

---

## Observability Tiers

| Tier | What It Does | Default State | Best For |
|------|-------------|---------------|----------|
| **Tier 1: Cloud Trace** | Distributed tracing — execution flow, latency, errors via OpenTelemetry spans | Always-on | Debugging latency, understanding agent execution flow |
| **Tier 2: Prompt-Response Logging** | GenAI interactions exported to GCS, BigQuery, and Cloud Logging | Disabled locally; enabled when deployed | Auditing LLM interactions, compliance |
| **Tier 3: BigQuery Agent Analytics** | Structured agent events (LLM calls, tool use, outcomes) to BigQuery | Opt-in (`--bq-analytics` at scaffold time) | Conversational analytics, custom dashboards, LLM-as-judge evals |
| **Tier 4: SLO Alerting** | SLO-based burn-rate alerts (availability, latency, safety) via Prometheus — fires only when error budget is genuinely at risk | Opt-in — requires Prometheus + Alertmanager stack | Production alerting for agentic AI services; replaces naive threshold alerts |

Ask the user which tier(s) they need — they can be combined. Tier 1 is mandatory; Tiers 2, 3, and 4 are additive.

---

## Quick Setup

### Tier 1: Cloud Trace (Always-On)

```python
# In your FastAPI app — scaffolded projects have this pre-configured
from google.adk.telemetry import setup_telemetry
setup_telemetry(otel_to_cloud=True)
```

View traces: **Cloud Console > Trace > Trace explorer**

### Tier 2: Prompt-Response Logging

```bash
# Enable locally
export LOGS_BUCKET_NAME="your-bucket-name"
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT="NO_CONTENT"
```

See `reference/cloud-trace-and-logging.md` for full infrastructure list, env vars, and verification commands.

### Tier 3: BigQuery Agent Analytics

```bash
# Enable at scaffold time
uvx agent-starter-pack create . --bq-analytics
```

See `reference/bigquery-agent-analytics.md` for post-scaffold manual setup and key features.

---

## Process

1. **Confirm tier(s)** — Ask which tiers the user needs before configuring anything
2. **Read reference files** — See `reference/cloud-trace-and-logging.md` (Tier 1 & 2) or `reference/bigquery-agent-analytics.md` (Tier 3) before writing any configuration
3. **Check env vars** — Verify all required environment variables are set (table in `reference/cloud-trace-and-logging.md`)
4. **Verify with commands** — Use the verification commands in `reference/cloud-trace-and-logging.md` to confirm telemetry is flowing
5. **Check costs** — High telemetry volume? Switch to `NO_CONTENT` mode; reduce BigQuery retention; disable unused tiers

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No traces in Cloud Trace | Verify `otel_to_cloud=True` in FastAPI app; check SA has `cloudtrace.agent` role |
| Prompt-response data missing | Check `LOGS_BUCKET_NAME` is set; verify SA has `storage.objectCreator`; check app logs |
| Privacy mode misconfigured | Check `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` — use `NO_CONTENT` for metadata-only |
| BigQuery Analytics not logging | Verify plugin in `app/agent.py`; check `BQ_ANALYTICS_DATASET_ID` env var |
| Traces missing tool spans | Tool spans appear under `execute_tool` — check trace explorer filters |

---

## Documentation Sources

| Topic | URL |
|-------|-----|
| Observability overview | `https://google.github.io/adk-docs/observability/index.md` |
| Agent activity logging | `https://google.github.io/adk-docs/observability/logging/index.md` |
| Cloud Trace integration | `https://google.github.io/adk-docs/integrations/cloud-trace/index.md` |
| BigQuery Agent Analytics | `https://google.github.io/adk-docs/integrations/bigquery-agent-analytics/index.md` |
