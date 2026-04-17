# NestJS Configuration — npm & TypeScript

Package configuration and TypeScript setup for NestJS 11.x. For Prisma 7.x schema and database configuration, see `nestjs-config-prisma7.md`.

## package.json

NestJS 11 backend service with enterprise-grade dependencies.

```json
{
  "name": "{project_name}",
  "version": "0.1.0",
  "description": "{description}",
  "author": "",
  "private": true,
  "license": "MIT",
  "scripts": {
    "build": "swc src -d dist --strip-leading-paths",
    "start": "node dist/main.js",
    "start:dev": "npm run build && node dist/main.js",
    "start:prod": "NODE_ENV=production node dist/main.js",
    "test": "vitest",
    "test:watch": "vitest --watch",
    "test:cov": "vitest run --coverage",
    "test:e2e": "vitest --config vitest.e2e.config.ts",
    "test:ci": "vitest run --coverage --reporter=junit --outputFile=./test-results/junit.xml",
    "lint": "eslint . --ext .ts,.tsx",
    "lint:fix": "eslint . --ext .ts,.tsx --fix",
    "format": "prettier --write \"src/**/*.ts\" \"test/**/*.ts\"",
    "format:check": "prettier --check \"src/**/*.ts\" \"test/**/*.ts\"",
    "prisma:generate": "prisma generate",
    "prisma:migrate": "prisma migrate dev",
    "prisma:migrate:deploy": "prisma migrate deploy",
    "prisma:seed": "tsx prisma/seeds/seed.ts",
    "prisma:studio": "prisma studio",
    "prisma:reset": "prisma migrate reset --force",
    "docker:dev": "docker-compose -f docker/docker-compose.dev.yml up -d",
    "docker:down": "docker-compose -f docker/docker-compose.dev.yml down",
    "docker:test": "docker-compose -f docker/docker-compose.test.yml up -d",
    "docker:build": "docker build -t {project_name}:latest .",
    "typecheck": "tsc --noEmit",
    "validate": "npm run typecheck && npm run lint && npm run test:ci",
    "prepare": "prisma generate"
  },
  "dependencies": {
    "@nestjs/common": "~11.17.0",
    "@nestjs/config": "~3.3.0",
    "@nestjs/core": "~11.17.0",
    "@nestjs/event-emitter": "~2.1.0",
    "@nestjs/platform-fastify": "~11.17.0",
    "@nestjs/schedule": "~4.1.0",
    "@nestjs/swagger": "~8.0.0",
    "@nestjs/terminus": "~11.17.0",
    "@nestjs/throttler": "~6.3.0",
    "@nestjs/bullmq": "~10.2.0",
    "@bull-board/api": "~5.21.0",
    "@bull-board/nestjs": "~5.21.0",
    "@bull-board/express": "~5.21.0",
    "bullmq": "~5.13.0",
    "@golevelup/nestjs-rabbitmq": "~5.5.0",
    "amqplib": "~0.10.4",
    "kafkajs": "~2.2.4",
    "@opentelemetry/api": "~1.9.0",
    "@opentelemetry/auto-instrumentations-node": "~0.50.0",
    "@opentelemetry/exporter-metrics-otlp-http": "~0.53.0",
    "@opentelemetry/exporter-trace-otlp-http": "~0.53.0",
    "@opentelemetry/resources": "~1.26.0",
    "@opentelemetry/sdk-metrics": "~1.26.0",
    "@opentelemetry/sdk-node": "~0.53.0",
    "@opentelemetry/sdk-trace-node": "~1.26.0",
    "@opentelemetry/semantic-conventions": "~1.26.0",
    "@prisma/adapter-pg": "~7.3.0",
    "@prisma/client": "~7.3.0",
    "pg": "~8.13.0",
    "axios": "~1.7.0",
    "class-transformer": "~0.5.1",
    "class-validator": "~0.14.1",
    "compression": "~1.7.4",
    "decimal.js": "~10.4.3",
    "dotenv": "~16.4.5",
    "@fastify/compress": "~8.0.0",
    "@fastify/helmet": "~12.0.0",
    "@fastify/static": "~8.0.0",
    "lru-cache": "~11.0.0",
    "redis": "~4.7.0",
    "reflect-metadata": "~0.2.2",
    "rxjs": "~7.8.1",
    "uuid": "~10.0.0",
    "zod": "~3.23.0"
  },
  "devDependencies": {
    "@eslint/js": "~9.15.0",
    "@nestjs/testing": "~11.17.0",
    "@swc/cli": "~0.4.0",
    "@swc/core": "~1.7.0",
    "@types/compression": "~1.7.5",
    "@types/node": "~22.9.0",
    "@types/uuid": "~10.0.0",
    "@typescript-eslint/eslint-plugin": "~8.15.0",
    "@typescript-eslint/parser": "~8.15.0",
    "@vitest/coverage-v8": "~2.1.0",
    "eslint": "~9.15.0",
    "eslint-config-prettier": "~9.1.0",
    "eslint-plugin-import": "~2.31.0",
    "eslint-plugin-promise": "~7.1.0",
    "eslint-plugin-security": "~3.0.0",
    "eslint-plugin-sonarjs": "~2.0.0",
    "prettier": "~3.4.0",
    "@types/pg": "~8.11.0",
    "prisma": "~7.3.0",
    "tsx": "~4.19.0",
    "typescript": "~5.9.x",
    "vitest": "~2.1.0"
  },
  "engines": {
    "node": ">=22.15.0",
    "pnpm": ">=9.0.0"
  },
  "packageManager": "pnpm@9.14.2"
}
```

## tsconfig.json

NestJS uses CommonJS module system with decorators and metadata reflection.

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "allowJs": false,
    "checkJs": false,
    "outDir": "./dist",
    "rootDir": "./src",
    "removeComments": true,
    "noEmit": false,
    "importHelpers": false,
    "downlevelIteration": true,
    "isolatedModules": true,

    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": false,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,

    "experimentalDecorators": true,
    "emitDecoratorMetadata": true,

    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,

    "sourceMap": true,
    "declaration": false,
    "declarationMap": false,
    "incremental": true,
    "tsBuildInfoFile": ".tsbuildinfo",

    "baseUrl": "./",
    "paths": {
      "@app/*": ["src/*"],
      "@config/*": ["src/config/*"],
      "@common/*": ["src/common/*"],
      "@core/*": ["src/core/*"],
      "@features/*": ["src/features/*"],
      "@shared/*": ["src/shared/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": [
    "node_modules",
    "dist",
    "test",
    "**/*.spec.ts",
    "**/*.test.ts",
    "**/*.e2e-spec.ts"
  ]
}
```
