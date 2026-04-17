# NestJS Observability & Logging

Observability patterns for NestJS 11.x covering OpenTelemetry tracing, metrics, and structured logging.

## Structured Logging Configuration

Configuration for structured logging with cloud provider support and request logging.

### Configuration File (`src/config/logging.config.ts`)

```typescript
/**
 * Structured Logging Configuration
 *
 * Supports multiple output formats and cloud logging providers:
 * - JSON format for production (GCP, AWS compatible)
 * - Pretty format for development
 * - Configurable log levels per environment
 */

import { registerAs } from '@nestjs/config';
import { getRequiredString, getOptionalString, getOptionalBoolean } from './static-config-reader';

export default registerAs('logging', () => ({
  // Log level: error, warn, log, debug, verbose
  level: getOptionalString('LOG_LEVEL') ?? 'info',

  // Output format: json, pretty
  format: getOptionalString('LOG_FORMAT') ?? 'json',

  // Include timestamps in logs
  timestamps: getOptionalBoolean('LOG_TIMESTAMPS') ?? true,

  // Service context for structured logging
  serviceContext: {
    service: getRequiredString('APP_NAME'),
    version: process.env.npm_package_version ?? '0.0.0',
    environment: getRequiredString('NODE_ENV'),
  },

  // Cloud logging configuration
  cloudLogging: {
    // Enable cloud logging integration
    enabled: getOptionalBoolean('CLOUD_LOGGING_ENABLED') ?? false,

    // GCP-specific
    gcpProjectId: getOptionalString('GCP_PROJECT_ID'),

    // AWS-specific
    awsRegion: getOptionalString('AWS_REGION'),
    awsLogGroup: getOptionalString('AWS_LOG_GROUP'),
  },

  // Request logging
  requestLogging: {
    // Log all requests
    enabled: getOptionalBoolean('LOG_REQUESTS') ?? true,

    // Fields to exclude from request body logging
    excludeFields: ['password', 'token', 'secret', 'apiKey', 'authorization'],

    // Max body size to log (bytes)
    maxBodySize: 10000,

    // Log slow requests (ms)
    slowRequestThreshold: 3000,
  },
}));
```

## OpenTelemetry Configuration

Configuration for distributed tracing and metrics collection via OpenTelemetry.

### Configuration File (`src/config/observability.config.ts`)

```typescript
/**
 * OpenTelemetry Observability Configuration
 *
 * Configures distributed tracing and metrics collection:
 * - OTLP exporters for traces and metrics
 * - Auto-instrumentation for common libraries
 * - Sampling strategies
 */

import { registerAs } from '@nestjs/config';
import { getOptionalString, getOptionalBoolean, getOptionalNumber } from './static-config-reader';

export default registerAs('observability', () => ({
  // Master switch for observability
  enabled: getOptionalBoolean('OTEL_ENABLED') ?? false,

  // Service identification
  serviceName: getOptionalString('OTEL_SERVICE_NAME') ?? process.env.APP_NAME ?? 'unknown-service',
  serviceVersion: process.env.npm_package_version ?? '0.0.0',
  deploymentEnvironment: process.env.NODE_ENV ?? 'development',

  // Tracing configuration
  tracing: {
    enabled: getOptionalBoolean('OTEL_TRACING_ENABLED') ?? true,

    // OTLP exporter endpoint
    endpoint: getOptionalString('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT') ??
              getOptionalString('OTEL_EXPORTER_OTLP_ENDPOINT') ??
              'http://localhost:4318/v1/traces',

    // Sampling rate (0.0 to 1.0)
    samplingRatio: getOptionalNumber('OTEL_TRACES_SAMPLER_ARG') ?? 1.0,

    // Always sample errors
    alwaysSampleErrors: true,
  },

  // Metrics configuration
  metrics: {
    enabled: getOptionalBoolean('OTEL_METRICS_ENABLED') ?? true,

    // OTLP exporter endpoint
    endpoint: getOptionalString('OTEL_EXPORTER_OTLP_METRICS_ENDPOINT') ??
              getOptionalString('OTEL_EXPORTER_OTLP_ENDPOINT') ??
              'http://localhost:4318/v1/metrics',

    // Export interval (ms)
    exportIntervalMs: getOptionalNumber('OTEL_METRIC_EXPORT_INTERVAL') ?? 60000,
  },

  // Instrumentation options
  instrumentation: {
    http: true,
    fastify: true,
    prisma: true,
    redis: true,
    dns: false, // Usually too noisy
    fs: false, // Usually too noisy
  },
}));
```

## OpenTelemetry Tracing Module

Module initialization for distributed tracing with automatic instrumentation.

### Tracing Module (`src/core/observability/tracing/tracing.module.ts`)

```typescript
/**
 * OpenTelemetry Tracing Module
 *
 * Initializes distributed tracing with automatic instrumentation
 */

import { Module, OnModuleInit, OnModuleDestroy, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION, ATTR_DEPLOYMENT_ENVIRONMENT } from '@opentelemetry/semantic-conventions';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-node';

@Module({})
export class TracingModule implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(TracingModule.name);
  private sdk: NodeSDK | null = null;

  constructor(private readonly configService: ConfigService) {}

  async onModuleInit(): Promise<void> {
    const enabled = this.configService.get<boolean>('observability.enabled');
    const tracingEnabled = this.configService.get<boolean>('observability.tracing.enabled');

    if (!enabled || !tracingEnabled) {
      this.logger.log('OpenTelemetry tracing is disabled');
      return;
    }

    try {
      const serviceName = this.configService.get<string>('observability.serviceName');
      const serviceVersion = this.configService.get<string>('observability.serviceVersion');
      const environment = this.configService.get<string>('observability.deploymentEnvironment');
      const endpoint = this.configService.get<string>('observability.tracing.endpoint');

      const resource = new Resource({
        [ATTR_SERVICE_NAME]: serviceName,
        [ATTR_SERVICE_VERSION]: serviceVersion,
        [ATTR_DEPLOYMENT_ENVIRONMENT]: environment,
      });

      const traceExporter = new OTLPTraceExporter({
        url: endpoint,
      });

      this.sdk = new NodeSDK({
        resource,
        spanProcessor: new BatchSpanProcessor(traceExporter),
        instrumentations: [
          getNodeAutoInstrumentations({
            '@opentelemetry/instrumentation-fs': { enabled: false },
            '@opentelemetry/instrumentation-dns': { enabled: false },
          }),
        ],
      });

      await this.sdk.start();
      this.logger.log(`OpenTelemetry tracing initialized - exporting to ${endpoint}`);
    } catch (error) {
      this.logger.error('Failed to initialize OpenTelemetry tracing', error);
    }
  }

  async onModuleDestroy(): Promise<void> {
    if (this.sdk) {
      await this.sdk.shutdown();
      this.logger.log('OpenTelemetry tracing shut down');
    }
  }
}
```

## Logging Interceptor

Global request/response logging interceptor with correlation ID tracking.

### Implementation (`src/common/interceptors/logging.interceptor.ts`)

```typescript
import { Injectable, NestInterceptor, ExecutionContext, CallHandler, Logger } from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

/**
 * Global Logging Interceptor
 *
 * Logs all incoming requests and responses with:
 * - Request method, URL, and correlation ID
 * - Response status and duration
 * - Errors with stack traces
 * - Automatic masking of sensitive fields
 */
@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger(LoggingInterceptor.name);
  private readonly sensitiveFields = ['password', 'token', 'secret', 'apiKey', 'authorization'];

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const request = context.switchToHttp().getRequest();
    const correlationId = request.headers['x-correlation-id'] ?? 'unknown';
    const { method, url } = request;

    this.logger.log(`[${correlationId}] → ${method} ${url}`);
    const start = Date.now();

    return next.handle().pipe(
      tap(() => {
        const response = context.switchToHttp().getResponse();
        const duration = Date.now() - start;
        this.logger.log(
          `[${correlationId}] ← ${method} ${url} ${response.statusCode} ${duration}ms`
        );
      }),
      catchError((error) => {
        const duration = Date.now() - start;
        this.logger.error(
          `[${correlationId}] ✗ ${method} ${url} ${error.status ?? 500} ${duration}ms`,
          error.stack
        );
        throw error;
      }),
    );
  }

  private maskSensitiveData(body: Record<string, unknown>): Record<string, unknown> {
    if (!body || typeof body !== 'object') {
      return body;
    }

    const masked = { ...body };
    for (const field of this.sensitiveFields) {
      if (field in masked) {
        masked[field] = '***REDACTED***';
      }
    }
    return masked;
  }
}
```

### Registration

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { LoggingInterceptor } from './common/interceptors/logging.interceptor';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Global logging interceptor
  app.useGlobalInterceptors(new LoggingInterceptor());

  await app.listen(3000);
}
bootstrap();
```

## Environment Configuration

### Base Configuration (`.env.example`)

```bash
# Base — observability disabled
OTEL_ENABLED=false
LOG_LEVEL=info
LOG_FORMAT=json
LOG_TIMESTAMPS=true
LOG_REQUESTS=true
```

### Development Configuration (`.env.development`)

```bash
# Development — pretty logs, no tracing
LOG_FORMAT=pretty
LOG_LEVEL=debug
OTEL_ENABLED=false
```

### Production Configuration (`.env.production`)

```bash
# Production — full observability
OTEL_ENABLED=true
OTEL_TRACING_ENABLED=true
OTEL_METRICS_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_SERVICE_NAME=my-nestjs-service
OTEL_TRACES_SAMPLER_ARG=1.0

# Structured logging
LOG_LEVEL=info
LOG_FORMAT=json
LOG_TIMESTAMPS=true
LOG_REQUESTS=true

# Cloud logging (if applicable)
CLOUD_LOGGING_ENABLED=true
GCP_PROJECT_ID=my-project
```

## Dependencies

Add these packages to your project:

```bash
npm install @opentelemetry/sdk-node \
  @opentelemetry/exporter-trace-otlp-http \
  @opentelemetry/resources \
  @opentelemetry/semantic-conventions \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/sdk-trace-node
```

## Troubleshooting

| Issue | Symptom | Fix |
|-------|---------|-----|
| Tracing not working | No spans exported | Check `OTEL_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT` is reachable |
| Too many spans | High cardinality, storage cost | Lower `OTEL_TRACES_SAMPLER_ARG` to 0.1 or 0.01 (1% sampling) |
| Missing correlation IDs | Logs show `unknown` | Ensure upstream services send `x-correlation-id` header or generate in middleware |
| Sensitive data in logs | Passwords appearing | Add field names to `sensitiveFields` array in interceptor |
| Noisy file system traces | Too many fs/dns spans | Verify `instrumentation.fs` and `instrumentation.dns` are `false` |
| Logs not structured | Text output instead of JSON | Set `LOG_FORMAT=json` in production environment |
