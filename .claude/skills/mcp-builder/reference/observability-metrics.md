## MCP Metrics Collection

Custom metrics using OpenTelemetry Metrics API:

```typescript
import { metrics } from '@opentelemetry/api';
import { Counter, Histogram, UpDownCounter, ObservableGauge } from '@opentelemetry/api';

const meter = metrics.getMeter('mcp-server-metrics');

// Counter: Total tool invocations
const toolInvocationsCounter = meter.createCounter('mcp_tool_invocations_total', {
  description: 'Total number of MCP tool invocations',
  unit: '1'
});

// Histogram: Tool execution duration
const toolDurationHistogram = meter.createHistogram('mcp_tool_duration_seconds', {
  description: 'MCP tool execution duration in seconds',
  unit: 's'
});

// Counter: Total tool errors
const toolErrorsCounter = meter.createCounter('mcp_tool_errors_total', {
  description: 'Total number of MCP tool errors',
  unit: '1'
});

// Counter: Abandon events — when agents give up mid-task
const toolAbandonsCounter = meter.createCounter('mcp_tool_abandons_total', {
  description: 'Total number of MCP tool calls abandoned by the agent',
  unit: '1'
  // label: reason ('timeout', 'circuit_open', 'max_retries', 'agent_decision')
});

// Histogram: Tools per task — how many calls agents make per user intent
const toolsPerTaskHistogram = meter.createHistogram('mcp_tools_per_task', {
  description: 'Number of MCP tool calls to complete one user task',
  unit: '1'
  // Record at task boundary: toolsPerTaskHistogram.record(callCount, { task_type })
  // P95 > 5 calls = consolidation opportunity (see mcp-design-principles.md 3-Step Rule)
});

// Counter: Token usage per tool (record input and output separately)
const toolTokensCounter = meter.createCounter('mcp_tool_tokens_total', {
  description: 'LLM tokens consumed by MCP tool responses',
  unit: '1'
  // labels: tool_name, direction ('input'|'output')
});

// Counter: Resource reads
const resourceReadsCounter = meter.createCounter('mcp_resource_reads_total', {
  description: 'Total number of MCP resource read operations',
  unit: '1'
});

// UpDownCounter: Active connections
const activeConnectionsCounter = meter.createUpDownCounter('mcp_active_connections', {
  description: 'Number of active MCP client connections',
  unit: '1'
});

// ObservableGauge: Circuit breaker state
let circuitBreakerStates: Map<string, number> = new Map();

const circuitBreakerGauge = meter.createObservableGauge('mcp_circuit_breaker_state', {
  description: 'Circuit breaker state (0=closed, 1=open, 2=half-open)',
  unit: '1'
});

circuitBreakerGauge.addCallback((observableResult) => {
  for (const [service, state] of circuitBreakerStates.entries()) {
    observableResult.observe(state, { service });
  }
});

export function updateCircuitBreakerState(service: string, state: 'closed' | 'open' | 'half-open') {
  const stateValue = state === 'closed' ? 0 : state === 'open' ? 1 : 2;
  circuitBreakerStates.set(service, stateValue);
}

// Helper function to instrument tool execution
export async function instrumentToolExecution<T>(
  toolName: string,
  fn: () => Promise<T>
): Promise<T> {
  const startTime = Date.now();

  try {
    const result = await fn();

    // Record successful invocation
    toolInvocationsCounter.add(1, {
      tool_name: toolName,
      success: 'true'
    });

    // Record duration
    const durationSeconds = (Date.now() - startTime) / 1000;
    toolDurationHistogram.record(durationSeconds, {
      tool_name: toolName
    });

    return result;
  } catch (error) {
    // Record failed invocation
    toolInvocationsCounter.add(1, {
      tool_name: toolName,
      success: 'false'
    });

    // Record error
    toolErrorsCounter.add(1, {
      tool_name: toolName,
      error_type: error instanceof Error ? error.constructor.name : 'UnknownError'
    });

    throw error;
  }
}

// Helper functions for other metrics
export function recordResourceRead(resourceType: string) {
  resourceReadsCounter.add(1, { resource_type: resourceType });
}

export function incrementActiveConnections() {
  activeConnectionsCounter.add(1);
}

export function decrementActiveConnections() {
  activeConnectionsCounter.add(-1);
}

// Usage example
// async function executeSearchTool(query: string) {
//   return instrumentToolExecution('search_products', async () => {
//     return searchDatabase(query);
//   });
// }
```

## Sampling Strategies

Per-tool cost control with adaptive sampling:

```typescript
import { Sampler, SamplingDecision, SamplingResult } from '@opentelemetry/sdk-trace-base';
import { Context, SpanKind, Attributes } from '@opentelemetry/api';

interface SamplingConfig {
  toolSampling: Record<string, number>; // Per-tool sampling rates (0.0-1.0)
  defaultSampling: {
    read: number;
    write: number;
    admin: number;
  };
  adaptiveSampling: {
    enabled: boolean;
    errorThreshold: number; // Error rate threshold to trigger high sampling
    highSamplingRate: number; // Sampling rate when errors are high
    cooldownMinutes: number; // Cooldown period after high sampling
  };
}

// Production sampling configuration
export const productionSamplingConfig: SamplingConfig = {
  toolSampling: {
    'process_payment': 1.0,        // Always trace payment operations
    'get_user_profile': 0.01,      // 1% sampling for read-heavy operations
    'search_products': 0.05,       // 5% sampling for searches
    'update_inventory': 0.1,       // 10% for writes
    'escalate_to_human': 1.0,      // Always trace escalations
    'generate_report': 0.02,       // 2% for expensive operations
    'send_notification': 0.001     // 0.1% for high-volume operations
  },
  defaultSampling: {
    read: 0.01,   // 1% for read operations
    write: 0.1,   // 10% for write operations
    admin: 1.0    // 100% for admin operations
  },
  adaptiveSampling: {
    enabled: true,
    errorThreshold: 0.05,      // Increase sampling if error rate > 5%
    highSamplingRate: 0.5,     // Sample 50% during high errors
    cooldownMinutes: 15        // Cool down for 15 minutes
  }
};

class MCPToolSampler implements Sampler {
  private config: SamplingConfig;
  private errorRateWindow: Array<{ timestamp: number; isError: boolean }> = [];
  private highSamplingUntil: number = 0;

  constructor(config: SamplingConfig) {
    this.config = config;
  }

  shouldSample(
    context: Context,
    traceId: string,
    spanName: string,
    spanKind: SpanKind,
    attributes: Attributes
  ): SamplingResult {
    // Extract tool name from span name or attributes
    const toolName = (attributes['tool.name'] as string) ||
                     spanName.replace('mcp.tool.', '');

    // Check if we're in adaptive high sampling mode
    if (this.config.adaptiveSampling.enabled) {
      const now = Date.now();

      // Check if still in high sampling cooldown
      if (now < this.highSamplingUntil) {
        if (Math.random() < this.config.adaptiveSampling.highSamplingRate) {
          return { decision: SamplingDecision.RECORD_AND_SAMPLED };
        }
      }

      // Calculate current error rate
      const errorRate = this.calculateErrorRate();
      if (errorRate > this.config.adaptiveSampling.errorThreshold) {
        this.highSamplingUntil = now + (this.config.adaptiveSampling.cooldownMinutes * 60 * 1000);
        return { decision: SamplingDecision.RECORD_AND_SAMPLED };
      }
    }

    // Per-tool sampling rate
    let samplingRate: number;

    if (toolName in this.config.toolSampling) {
      samplingRate = this.config.toolSampling[toolName];
    } else {
      // Determine operation type from attributes
      const operationType = (attributes['operation.type'] as string) || 'read';
      samplingRate = this.config.defaultSampling[operationType as keyof typeof this.config.defaultSampling]
                     || this.config.defaultSampling.read;
    }

    // Make sampling decision
    const shouldSample = Math.random() < samplingRate;

    return {
      decision: shouldSample
        ? SamplingDecision.RECORD_AND_SAMPLED
        : SamplingDecision.NOT_RECORD
    };
  }

  toString(): string {
    return 'MCPToolSampler';
  }

  private calculateErrorRate(): number {
    const now = Date.now();
    const fiveMinutesAgo = now - (5 * 60 * 1000);

    // Clean old entries
    this.errorRateWindow = this.errorRateWindow.filter(
      entry => entry.timestamp > fiveMinutesAgo
    );

    if (this.errorRateWindow.length === 0) return 0;

    const errorCount = this.errorRateWindow.filter(e => e.isError).length;
    return errorCount / this.errorRateWindow.length;
  }

  recordExecution(isError: boolean) {
    this.errorRateWindow.push({
      timestamp: Date.now(),
      isError
    });
  }
}

// Usage in NodeSDK initialization
// import { MCPToolSampler, productionSamplingConfig } from './observability';
//
// const sdk = new NodeSDK({
//   resource,
//   traceExporter,
//   sampler: new MCPToolSampler(productionSamplingConfig),
//   // ... other config
// });
```
