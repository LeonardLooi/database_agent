# Agentic AI Observability

LangSmith tracing, Prometheus metrics, structured logging, and alerting for production AI agents.

## LangSmith Setup

**File:** `src/<service>/observability/tracing.py`

```python
from __future__ import annotations

import os
from functools import wraps

from langsmith import Client, traceable

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


def setup_langsmith() -> Client | None:
    """Initialize LangSmith client for tracing.

    Requires LANGSMITH_API_KEY and LANGSMITH_PROJECT in environment.
    Returns None if not configured (non-blocking).
    """
    if not settings.langsmith_api_key:
        logger.info("langsmith_disabled", reason="No API key configured")
        return None

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    client = Client()
    logger.info("langsmith_enabled", project=settings.langsmith_project)
    return client


def trace_agent(name: str, metadata: dict | None = None):
    """Decorator to trace agent functions in LangSmith.

    Usage:
        @trace_agent("react_agent")
        async def invoke_agent(state):
            ...
    """
    def decorator(func):
        @wraps(func)
        @traceable(name=name, metadata=metadata or {})
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Custom LangSmith Evaluators

```python
from langsmith.evaluation import EvaluationResult, run_evaluator


@run_evaluator
def groundedness_evaluator(run, example) -> EvaluationResult:
    """Evaluate if the agent's response is grounded in retrieved documents."""
    # Get the agent output and retrieved docs from the run
    output = run.outputs.get("output", "")
    docs = run.outputs.get("documents", [])

    if not docs:
        return EvaluationResult(key="groundedness", score=0.0, comment="No documents retrieved")

    # Use LLM to check groundedness
    # (In practice, use a dedicated evaluation model)
    score = 1.0 if any(doc_text in output for doc_text in docs) else 0.5

    return EvaluationResult(key="groundedness", score=score)


@run_evaluator
def tool_usage_evaluator(run, example) -> EvaluationResult:
    """Evaluate if the agent used appropriate tools."""
    # Check intermediate steps for tool usage
    steps = run.outputs.get("intermediate_steps", [])
    expected_tools = example.outputs.get("expected_tools", [])

    used_tools = [step.get("tool") for step in steps if "tool" in step]
    correct = len(set(used_tools) & set(expected_tools))
    total = max(len(expected_tools), 1)

    return EvaluationResult(
        key="tool_usage",
        score=correct / total,
        comment=f"Used {used_tools}, expected {expected_tools}",
    )
```

## Prometheus Metrics

**File:** `src/<service>/observability/metrics.py`

```python
from __future__ import annotations

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from ..core.logging import get_logger

logger = get_logger(__name__)

# --- Agent Metrics ---

AGENT_INVOCATIONS = Counter(
    "agent_invocations_total",
    "Total agent invocations",
    ["agent_name", "status"],  # status: success, error, timeout
)

AGENT_LATENCY = Histogram(
    "agent_latency_seconds",
    "Agent invocation latency",
    ["agent_name"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

AGENT_ITERATIONS = Histogram(
    "agent_iterations_total",
    "Number of iterations per agent invocation",
    ["agent_name"],
    buckets=[1, 2, 3, 5, 10, 15, 20, 25],
)

# --- LLM Metrics ---

LLM_CALLS = Counter(
    "llm_calls_total",
    "Total LLM API calls",
    ["provider", "model", "status"],
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total tokens consumed",
    ["provider", "model", "direction"],  # direction: input, output
)

LLM_LATENCY = Histogram(
    "llm_latency_seconds",
    "LLM API call latency",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)

LLM_COST = Counter(
    "llm_cost_usd_total",
    "Estimated LLM cost in USD",
    ["provider", "model"],
)

# --- Tool Metrics ---

TOOL_CALLS = Counter(
    "tool_calls_total",
    "Total tool invocations",
    ["tool_name", "status"],
)

TOOL_LATENCY = Histogram(
    "tool_latency_seconds",
    "Tool execution latency",
    ["tool_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# --- RAG Metrics ---

RAG_RETRIEVAL_COUNT = Histogram(
    "rag_documents_retrieved",
    "Number of documents retrieved per query",
    ["retriever"],
    buckets=[0, 1, 3, 5, 10, 20],
)

RAG_RELEVANCE_SCORE = Histogram(
    "rag_relevance_score",
    "Relevance score of retrieved documents",
    ["retriever"],
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
)

# --- System Metrics ---

ACTIVE_THREADS = Gauge(
    "active_threads",
    "Number of active conversation threads",
)

GUARDRAIL_BLOCKS = Counter(
    "guardrail_blocks_total",
    "Guardrail violations blocked",
    ["layer"],
)


def setup_prometheus(app: FastAPI) -> None:
    """Add Prometheus metrics endpoint to FastAPI app."""

    @app.get("/metrics")
    async def metrics():
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    logger.info("prometheus_metrics_enabled")
```

## Critical Metrics Dashboard

Key metrics to monitor in production:

| Category | Metric | Alert Threshold |
|----------|--------|-----------------|
| **Latency** | `agent_latency_seconds` p95 | > 30s |
| **Latency** | `llm_latency_seconds` p95 | > 10s |
| **Quality** | `rag_relevance_score` avg | < 0.5 |
| **Cost** | `llm_cost_usd_total` daily | > budget |
| **Reliability** | `agent_invocations_total{status=error}` rate | > 5% |
| **Reliability** | `tool_calls_total{status=error}` rate | > 10% |
| **Safety** | `guardrail_blocks_total` rate | > 1% |
| **Throughput** | `agent_invocations_total` rate | varies |

## Structured Logging with Correlation IDs

```python
import time
from functools import wraps

import structlog


def log_agent_execution(agent_name: str):
    """Decorator that logs agent execution with timing and context."""
    def decorator(func):
        @wraps(func)
        async def wrapper(state, *args, **kwargs):
            log = structlog.get_logger(agent_name)
            thread_id = state.get("thread_id", "unknown")
            iteration = state.get("iteration_count", 0)

            log.info(
                "node_start",
                agent_name=agent_name,
                thread_id=thread_id,
                iteration=iteration,
                message_count=len(state.get("messages", [])),
            )

            start = time.monotonic()
            try:
                result = await func(state, *args, **kwargs)
                duration = time.monotonic() - start

                log.info(
                    "node_complete",
                    agent_name=agent_name,
                    thread_id=thread_id,
                    iteration=iteration,
                    duration_ms=round(duration * 1000),
                )

                AGENT_LATENCY.labels(agent_name=agent_name).observe(duration)
                AGENT_INVOCATIONS.labels(agent_name=agent_name, status="success").inc()
                return result

            except Exception as e:
                duration = time.monotonic() - start
                log.error(
                    "node_failed",
                    agent_name=agent_name,
                    thread_id=thread_id,
                    error=str(e),
                    duration_ms=round(duration * 1000),
                )
                AGENT_INVOCATIONS.labels(agent_name=agent_name, status="error").inc()
                raise

        return wrapper
    return decorator


# Usage
@log_agent_execution("react_agent")
async def agent_node(state: AgentState) -> dict:
    ...
```

## Alerting Rules

```yaml
# Prometheus alerting rules (prometheus/alerts.yml)
groups:
  - name: agent_alerts
    rules:
      - alert: HighAgentLatency
        expr: histogram_quantile(0.95, agent_latency_seconds_bucket) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Agent p95 latency > 30s"

      - alert: HighErrorRate
        expr: rate(agent_invocations_total{status="error"}[5m]) / rate(agent_invocations_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Agent error rate > 5%"

      - alert: LLMCostBudget
        expr: increase(llm_cost_usd_total[24h]) > 100
        labels:
          severity: warning
        annotations:
          summary: "Daily LLM cost exceeded $100"

      - alert: GuardrailViolations
        expr: rate(guardrail_blocks_total[1h]) > 0.01
        labels:
          severity: warning
        annotations:
          summary: "Guardrail blocking > 1% of requests"
```
