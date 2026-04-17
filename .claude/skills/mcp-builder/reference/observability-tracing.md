# OpenTelemetry Observability Stack for Production MCP Servers

This document provides production-ready OpenTelemetry instrumentation patterns for MCP servers, including tracing, metrics, and adaptive sampling strategies.

## Dependencies

```json
{
  "@opentelemetry/sdk-node": "~0.57.0",
  "@opentelemetry/auto-instrumentations-node": "~0.54.0",
  "@opentelemetry/exporter-trace-otlp-http": "~0.57.0",
  "@opentelemetry/exporter-metrics-otlp-http": "~0.57.0",
  "@opentelemetry/resources": "~1.29.0",
  "@opentelemetry/semantic-conventions": "~1.29.0",
  "@opentelemetry/api": "~1.9.0"
}
```

## Tracing Setup

Full initialization function with NodeSDK, auto-instrumentation, and OTLP exporters:

```typescript
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION, ATTR_DEPLOYMENT_ENVIRONMENT } from '@opentelemetry/semantic-conventions';
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';

interface ObservabilityConfig {
  serviceName: string;
  serviceVersion: string;
  environment: 'development' | 'staging' | 'production';
  otlpEndpoint?: string;
  enableAutoInstrumentation?: boolean;
}

export function initializeObservability(config: ObservabilityConfig): NodeSDK {
  const {
    serviceName,
    serviceVersion,
    environment,
    otlpEndpoint = 'http://localhost:4318',
    enableAutoInstrumentation = true
  } = config;

  // Create resource with service metadata
  const resource = new Resource({
    [ATTR_SERVICE_NAME]: serviceName,
    [ATTR_SERVICE_VERSION]: serviceVersion,
    [ATTR_DEPLOYMENT_ENVIRONMENT]: environment
  });

  // Configure OTLP trace exporter
  const traceExporter = new OTLPTraceExporter({
    url: `${otlpEndpoint}/v1/traces`,
    headers: {}
  });

  // Configure OTLP metrics exporter with 10s export interval
  const metricReader = new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({
      url: `${otlpEndpoint}/v1/metrics`,
      headers: {}
    }),
    exportIntervalMillis: 10000 // 10 seconds
  });

  // Initialize NodeSDK
  const sdk = new NodeSDK({
    resource,
    traceExporter,
    metricReader,
    instrumentations: enableAutoInstrumentation
      ? [getNodeAutoInstrumentations()]
      : []
  });

  // Start the SDK
  sdk.start();

  // Graceful shutdown on process termination
  process.on('SIGTERM', () => {
    sdk.shutdown()
      .then(() => console.log('OpenTelemetry SDK shut down successfully'))
      .catch((error) => console.error('Error shutting down OpenTelemetry SDK', error))
      .finally(() => process.exit(0));
  });

  return sdk;
}

// Usage example
// const sdk = initializeObservability({
//   serviceName: 'my-mcp-server',
//   serviceVersion: '1.0.0',
//   environment: 'production',
//   otlpEndpoint: process.env.OTEL_EXPORTER_OTLP_ENDPOINT
// });
```

## Custom MCP Spans

Wrapper function to create custom spans for MCP tool executions:

```typescript
import { trace, context, SpanKind, SpanStatusCode } from '@opentelemetry/api';

const tracer = trace.getTracer('mcp-server');

interface SpanAttributes {
  [key: string]: string | number | boolean;
}

export async function withTracing<T>(
  spanName: string,
  attributes: SpanAttributes,
  fn: () => Promise<T>
): Promise<T> {
  return tracer.startActiveSpan(
    spanName,
    { kind: SpanKind.SERVER, attributes },
    async (span) => {
      try {
        const result = await fn();
        span.setStatus({ code: SpanStatusCode.OK });
        return result;
      } catch (error) {
        span.setStatus({
          code: SpanStatusCode.ERROR,
          message: error instanceof Error ? error.message : 'Unknown error'
        });

        // Record exception with stack trace
        span.recordException(error as Error);

        throw error;
      } finally {
        span.end();
      }
    }
  );
}

// Usage example for MCP tool
// async function executeTool(toolName: string, params: unknown) {
//   return withTracing(
//     `mcp.tool.${toolName}`,
//     {
//       'tool.name': toolName,
//       'tool.params': JSON.stringify(params),
//       'mcp.version': '1.0'
//     },
//     async () => {
//       // Tool execution logic
//       return performToolOperation(params);
//     }
//   );
// }
```

## The 6-Metric Pyramid

Build observability in this order. Each layer depends on the one below — you cannot optimize costs without understanding behavior first.

```
Layer 4: Cost (Top)
    └─ Token Usage — input/output tokens per tool, cost per operation

Layer 3: Reliability
    └─ Abandon Rate — when and why agents give up mid-task

Layer 2: Performance
    ├─ Average Response Times — P50/P95/P99 latency per tool
    └─ Error Rates — failure patterns per tool and error type

Layer 1: Behavior (Foundation — start here)
    ├─ Tool Selection Frequency — which tools are actually called and how often
    └─ Tools Per Task — how many tool calls agents make to complete one user intent
```

**Start at Layer 1, not Layer 4.** The most common mistake is instrumenting token costs first. Without behavioral data, you optimize the wrong tools. The engineering team that found their `document_search` was consuming 62% of token budget despite only 26% of invocations could only see that after Layer 1 data existed.

**Prometheus metrics for all 6:**
```
mcp_tool_invocations_total{tool_name, server}          # Tool Selection Frequency
mcp_tools_per_task_histogram{session_id}               # Tools Per Task
mcp_tool_duration_seconds{tool_name, quantile}         # Response Times
mcp_tool_errors_total{tool_name, error_type}           # Error Rates
mcp_tool_abandons_total{tool_name, reason}             # Abandon Rate
mcp_tool_tokens_total{tool_name, direction}            # Token Usage
```

