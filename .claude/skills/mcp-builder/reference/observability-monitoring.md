## Integration Example

Complete example showing initialization and usage:

```typescript
import { initializeObservability } from './observability/tracing.js';
import {
  instrumentToolExecution,
  recordResourceRead,
  incrementActiveConnections,
  decrementActiveConnections
} from './observability/metrics.js';
import { withTracing } from './observability/tracing.js';

// Initialize on server startup
const sdk = initializeObservability({
  serviceName: 'payment-mcp-server',
  serviceVersion: '2.1.0',
  environment: 'production',
  otlpEndpoint: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318'
});

// Instrument MCP tool handler
async function handleToolCall(toolName: string, params: unknown) {
  return instrumentToolExecution(toolName, async () => {
    return withTracing(
      `mcp.tool.${toolName}`,
      {
        'tool.name': toolName,
        'tool.params_size': JSON.stringify(params).length,
        'mcp.protocol_version': '1.0'
      },
      async () => {
        switch (toolName) {
          case 'process_payment':
            return processPayment(params);
          case 'get_user_profile':
            recordResourceRead('user_profile');
            return getUserProfile(params);
          default:
            throw new Error(`Unknown tool: ${toolName}`);
        }
      }
    );
  });
}

// Track connections
function onClientConnected() {
  incrementActiveConnections();
}

function onClientDisconnected() {
  decrementActiveConnections();
}
```

## Best Practices

1. **Always sample critical operations** - Payment processing, authentication, escalations should have 1.0 sampling rate
2. **Use adaptive sampling** - Automatically increase sampling during incidents when error rates spike
3. **Monitor high-cardinality attributes** - Avoid adding user IDs or request IDs directly to metric labels
4. **Set export intervals appropriately** - 10s for metrics, immediate for traces in production
5. **Use semantic conventions** - Follow OpenTelemetry semantic conventions for attribute naming
6. **Implement graceful shutdown** - Always shut down SDK on SIGTERM to flush remaining data
7. **Record exceptions properly** - Use `span.recordException()` to capture stack traces
8. **Test sampling rates in staging** - Verify your sampling configuration doesn't miss critical traces before deploying to production

---

## Post-Deployment Health Targets

After deploying any MCP server to production, monitor these metrics for the first 24 hours. If any target is missed, investigate before declaring the deployment stable.

| Metric | Healthy Target | Alert Threshold | Action |
|--------|---------------|----------------|--------|
| Tool selection accuracy | > 90% | < 85% | Review tool descriptions — likely a language break |
| Token overhead per task | < 5,000 tokens | > 8,000 tokens | Review Progressive Disclosure — responses too large |
| Circuit breaker open rate | < 1% | > 3% | Upstream service issue — check upstream health |
| Task completion in ≤ 3 tool calls | > 80% | < 70% | Tool design issue — consolidate tools by intent |
| Tool error rate (overall) | < 2% | > 5% | Rollback or hotfix |
| P99 tool latency | < 2,000ms | > 5,000ms | Check upstream timeouts and retry config |
| Suggestion override rate | 5%–15% | < 5% or > 25% | Suggestions too obvious (< 5%) or misleading (> 25%) |

**Suggestion override rate** is measured by tracking when agents call a tool OTHER than the one suggested in `next_actions`. A healthy rate is 5–15%. If agents always follow suggestions (< 5%), suggestions may be unnecessary noise. If agents rarely follow them (> 25%), the suggestions are wrong — review the agent-directive logic.

### Reasoning Atrophy Detection

Over-prescription of directives causes agents to stop deliberating. Two signals to track:

**1. Reasoning trace depth** — Count the steps in the agent's chain-of-thought per decision. If median trace depth decreases week-over-week by more than 10%, agents are taking shortcuts instead of reasoning. Stable or increasing depth is healthy.

```python
# Measure from agent logs — count CoT steps before tool call
weekly_median_trace_depth = median([len(trace.steps) for trace in weekly_decisions])
if week_over_week_change(weekly_median_trace_depth) < -0.10:
    log_warning("Reasoning trace depth declining — possible directive over-prescription")
```

**2. No-suggestion recovery time** (A/B baseline) — Withhold directives from 5% of responses randomly. Measure agent decision latency for those responses vs. normal.

| Ratio (no-suggestion latency / normal latency) | Interpretation |
|---|---|
| < 2× | Agent reasons independently — healthy |
| 2–5× | Moderate suggestion dependency |
| > 5× or timeout | Severe dependency — review directive distribution |

```typescript
// Server-side: randomly withhold directives for 5% of responses
if (Math.random() < 0.05) {
  delete response.next_actions;
  delete response.directive;
  response._baseline_test = true;  // Tag for metric separation
}
```

Track `decision_latency_ms` tagged by `baseline_test: true/false` in your metrics pipeline. Compare distributions weekly.

### Grafana Dashboard Layout

Organize dashboards in three tiers:

```
Top row (health): error_rate, p99_latency, circuit_breaker_state, active_connections
Middle row (diagnostic): tool_invocations by tool_name, token_usage, cache_hit_ratio
Bottom row (deep): per-tool error breakdown, sampling rate, resource reads
```

Alert routing: Top row alerts → PagerDuty (wake someone up). Middle row → Slack warning channel. Bottom row → async review only.

### Three-Tier Alert Thresholds

Alert fatigue kills observability programs. Teams disable noisy alerts and then miss real incidents. Configure exactly three tiers with specific thresholds:

**Tier 1 — Critical (page immediately, any hour):**
- Error rate > 50% for ≥ 2 minutes
- Abandon rate > 25% for ≥ 10 minutes

These fire rarely. When they do, someone wakes up. No exceptions. If Tier 1 fires more than once per week, the threshold is wrong — tune it.

**Tier 2 — Warning (Slack, investigate today):**
- P95 latency > 1.5× SLO for ≥ 15 minutes
- Error rate > 5% for ≥ 15 minutes

Degradation, not outage. Create a ticket. Do not page.

**Tier 3 — Info (daily digest, trends only):**
- Daily token cost exceeded budget by 20%
- Tool invocation volume spiked 50% above 7-day baseline

These are trend signals, not emergencies. Batch them into a daily report.

**Rule:** Tier 1 : Tier 2 ratio should be roughly 1:5. If they're equal, Tier 1 thresholds are too permissive.

### Cost Reduction Playbook

Apply these three optimizations in sequence — each requires the previous layer's data to identify the right targets.

**Step 1 — Caching (easiest, fastest ROI)**
- Identify highest-frequency tools with low response variance (FAQ lookups, catalog reads, profile fetches)
- Add 5-minute TTL cache for these tools
- Typical result: 30-40% reduction in invocations for cached tools
- Requires: Tool Selection Frequency data (Layer 1)

**Step 2 — Model routing (architectural, highest savings)**
- Identify tools where simple queries dominate (weather lookups, calendar reads, status checks)
- Route these to smaller/cheaper models (e.g., route 60% of reads away from largest model)
- Typical result: 50-70% cost reduction on routed calls
- Requires: Tools Per Task + token usage data to confirm which calls are genuinely simple
- Trade-off: Smaller models have lower capability — validate accuracy before routing in production

**Step 3 — Context compression (behavioral fix)**
- Identify tools where token usage/call is significantly above target (>2× expected)
- Add pre-LLM summarization for large response payloads (full document → summary before LLM reasoning)
- Typical result: 40-50% token reduction on affected tools
- Requires: Token Usage per tool data (Layer 4)
