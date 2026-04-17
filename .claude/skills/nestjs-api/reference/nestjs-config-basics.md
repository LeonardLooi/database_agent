# NestJS Configuration Basics

Fail-fast configuration patterns with static config reader and module aggregation for NestJS 11.x.

## Static Configuration Reader

All environment variable validation happens in a centralized reader with fail-fast behavior.

**File:** `src/config/static-config-reader.ts`

```typescript
/**
 * Static Configuration Reader
 *
 * PRINCIPLES:
 * - NO hardcoded defaults
 * - NO fallback values
 * - ALL validation happens here
 * - Application FAILS FAST if configs are missing
 */

import { StaticConfigurationException } from '../common/exceptions/static-configuration.exception';

const NON_EMPTY_STRING_MSG = 'non-empty string';

/**
 * Get required string environment variable
 * @throws {StaticConfigurationException} if variable is missing or empty
 */
export const getRequiredString = (key: string): string => {
  if (!key) {
    throw StaticConfigurationException.invalidEnvVar('key', key, NON_EMPTY_STRING_MSG);
  }

  const value = process.env[key];
  if (value === undefined || value.trim() === '') {
    throw StaticConfigurationException.missingEnvVar(key);
  }

  return value.trim();
};

/**
 * Get required numeric environment variable
 * @throws {StaticConfigurationException} if variable is missing or not a valid number
 */
export const getRequiredNumber = (key: string): number => {
  if (!key) {
    throw StaticConfigurationException.invalidEnvVar('key', key, NON_EMPTY_STRING_MSG);
  }

  const value = process.env[key];
  if (value === undefined || value.trim() === '') {
    throw StaticConfigurationException.missingEnvVar(key);
  }

  const parsed = parseFloat(value);
  if (isNaN(parsed)) {
    throw StaticConfigurationException.invalidEnvVar(key, value, 'number');
  }

  return parsed;
};

/**
 * Get required integer environment variable
 */
export const getRequiredInt = (key: string): number => {
  if (!key) {
    throw StaticConfigurationException.invalidEnvVar('key', key, NON_EMPTY_STRING_MSG);
  }

  const value = process.env[key];
  if (value === undefined || value.trim() === '') {
    throw StaticConfigurationException.missingEnvVar(key);
  }

  const parsed = parseInt(value, 10);
  if (isNaN(parsed)) {
    throw StaticConfigurationException.invalidEnvVar(key, value, 'integer');
  }

  return parsed;
};

/**
 * Get required boolean environment variable
 */
export const getRequiredBoolean = (key: string): boolean => {
  if (!key) {
    throw StaticConfigurationException.invalidEnvVar('key', key, NON_EMPTY_STRING_MSG);
  }

  const value = process.env[key];
  if (value === undefined || value === '') {
    throw StaticConfigurationException.missingEnvVar(key);
  }

  const lowerValue = value.toLowerCase().trim();
  if (lowerValue !== 'true' && lowerValue !== 'false') {
    throw StaticConfigurationException.invalidEnvVar(key, value, 'boolean (true/false)');
  }

  return lowerValue === 'true';
};

/**
 * Get required JSON environment variable
 */
export const getRequiredJson = <T = unknown>(key: string): T => {
  if (!key) {
    throw StaticConfigurationException.invalidEnvVar('key', key, NON_EMPTY_STRING_MSG);
  }

  const value = process.env[key];
  if (value === undefined || value === '') {
    throw StaticConfigurationException.missingEnvVar(key);
  }

  try {
    return JSON.parse(value) as T;
  } catch {
    throw StaticConfigurationException.invalidEnvVar(key, value, 'valid JSON');
  }
};

/**
 * Get required string array environment variable (comma-separated)
 */
export const getRequiredStringArray = (key: string): string[] => {
  if (!key) {
    throw StaticConfigurationException.invalidEnvVar('key', key, NON_EMPTY_STRING_MSG);
  }

  const value = process.env[key];
  if (value === undefined || value === '') {
    throw StaticConfigurationException.missingEnvVar(key);
  }

  return value.split(',').map(item => item.trim()).filter(item => item !== '');
};

/**
 * Get optional string array environment variable
 */
export const getOptionalArray = (key: string): string[] => {
  if (!key) {
    throw StaticConfigurationException.invalidEnvVar('key', key, NON_EMPTY_STRING_MSG);
  }

  const value = process.env[key];
  if (value === undefined || value === '') {
    return [];
  }

  return value.split(',').map(item => item.trim()).filter(item => item !== '');
};

/**
 * Get optional environment variable
 */
export const getOptionalString = (key: string): string | undefined => {
  if (!key) {
    throw StaticConfigurationException.invalidEnvVar('key', key, NON_EMPTY_STRING_MSG);
  }

  const value = process.env[key];
  if (value === undefined) {
    return undefined;
  }

  const trimmed = value.trim();
  return trimmed === '' ? undefined : trimmed;
};

/**
 * Get optional numeric environment variable
 */
export const getOptionalNumber = (key: string): number | undefined => {
  if (!key) {
    throw StaticConfigurationException.invalidEnvVar('key', key, NON_EMPTY_STRING_MSG);
  }

  const value = process.env[key];
  if (value === undefined || value.trim() === '') {
    return undefined;
  }

  const parsed = parseFloat(value);
  if (isNaN(parsed)) {
    throw StaticConfigurationException.invalidEnvVar(key, value, 'number or leave unset');
  }

  return parsed;
};

/**
 * Get optional boolean environment variable
 */
export const getOptionalBoolean = (key: string): boolean | undefined => {
  if (!key) {
    throw StaticConfigurationException.invalidEnvVar('key', key, NON_EMPTY_STRING_MSG);
  }

  const value = process.env[key];
  if (value === undefined || value === '') {
    return undefined;
  }

  const lowerValue = value.toLowerCase().trim();
  if (lowerValue !== 'true' && lowerValue !== 'false') {
    throw StaticConfigurationException.invalidEnvVar(key, value, 'boolean (true/false) or leave unset');
  }

  return lowerValue === 'true';
};

/**
 * Validate that all required environment variables are present
 */
export const validateRequiredEnvVars = (requiredVars: string[]): void => {
  const missing: string[] = [];

  for (const varName of requiredVars) {
    const value = process.env[varName];
    if (value === undefined || value.trim() === '') {
      missing.push(varName);
    }
  }

  if (missing.length > 0) {
    const errorMsg = `Missing required environment variables:\n${missing.map(v => `  - ${v}`).join('\n')}\n\nPlease add these to your .env file.`;
    throw new StaticConfigurationException(errorMsg);
  }
};
```

## Configuration Module

The root configuration module aggregates ALL individual config files.

**File:** `src/config/config.module.ts`

```typescript
/**
 * Configuration Module
 *
 * THE SINGLE AGGREGATOR for ALL configuration files.
 *
 * Architecture Pattern: Module Aggregation
 * - Single entry point for all configurations
 * - Ensures all configs are loaded at startup
 */

import { Module } from '@nestjs/common';
import { ConfigModule as NestConfigModule } from '@nestjs/config';

// Core application configurations
import apiConfig from './api.config';
import applicationConfig from './application.config';
import cacheConfig from './cache.config';
import databaseConfig from './database.config';
import healthConfig from './health.config';
import resilienceConfig from './resilience.config';
import securityConfig from './security.config';
import throttlerConfig from './throttler.config';

export const ALL_CONFIGS = [
  applicationConfig,
  databaseConfig,
  cacheConfig,
  securityConfig,
  apiConfig,
  resilienceConfig,
  throttlerConfig,
  healthConfig,
];

@Module({
  imports: [
    NestConfigModule.forRoot({
      isGlobal: true,
      cache: true,
      expandVariables: true,
      load: ALL_CONFIGS,
      validationOptions: {
        allowUnknown: false,
        abortEarly: true,
      },
    }),
  ],
  exports: [NestConfigModule],
})
export class ConfigModule {}

// Export individual configs for direct usage if needed
export {
  apiConfig,
  applicationConfig,
  cacheConfig,
  databaseConfig,
  healthConfig,
  resilienceConfig,
  securityConfig,
  throttlerConfig,
};
```

## Individual Config File Pattern

Each config file uses `registerAs()` from `@nestjs/config` and the static config reader for validation.

**Example:** `src/config/logging.config.ts`

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

## Key Patterns

| Pattern | Description |
|---------|-------------|
| Fail-fast validation | All required env vars validated at startup via static config reader |
| No hardcoded defaults | Every value comes from environment or explicit fallback in config |
| Type-safe configs | Use `registerAs()` for namespaced, type-safe config access |
| Global config module | `isGlobal: true` makes ConfigService available everywhere |

## Usage in Services

```typescript
import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class MyService {
  constructor(private readonly configService: ConfigService) {}

  someMethod() {
    // Access namespaced config
    const logLevel = this.configService.get<string>('logging.level');
    const dbUrl = this.configService.get<string>('database.url');

    // Type-safe with inference
    const config = this.configService.get<{
      level: string;
      format: string;
    }>('logging');
  }
}
```
