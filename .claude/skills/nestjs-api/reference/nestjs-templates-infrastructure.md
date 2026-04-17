# NestJS Infrastructure Templates — Docker, Compose, Testing

Production-ready Docker, Docker Compose, and testing configuration templates for NestJS 11.x.

## Dockerfile

```dockerfile
# my-service - Multi-Stage Production Dockerfile
# Security-hardened, minimal image with non-root user

# ============================================
# Stage 1: Base with pnpm
# ============================================
FROM node:24-alpine AS base

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Security: create non-root user early
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nestjs

# ============================================
# Stage 2: Dependencies
# ============================================
FROM base AS deps

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./
COPY prisma ./prisma/

# Install dependencies (including devDependencies for build)
RUN pnpm install --frozen-lockfile

# ============================================
# Stage 3: Builder
# ============================================
FROM base AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Generate Prisma client
RUN pnpm prisma generate

# Build the application
RUN pnpm build

# Remove devDependencies for production
RUN pnpm prune --prod

# ============================================
# Stage 4: Production Runner
# ============================================
FROM base AS runner

WORKDIR /app

# Set production environment
ENV NODE_ENV=production
ENV PORT=3000

# Security: use non-root user
USER nestjs

# Copy built application with correct ownership
COPY --from=builder --chown=nestjs:nodejs /app/dist ./dist
COPY --from=builder --chown=nestjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nestjs:nodejs /app/package.json ./
COPY --from=builder --chown=nestjs:nodejs /app/prisma ./prisma

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health/live || exit 1

# Expose port
EXPOSE 3000

# Start the application
CMD ["node", "dist/main.js"]
```

## Docker Compose (Development)

```yaml
# docker-compose.dev.yml - Development Environment
version: '3.9'

services:
  # PostgreSQL Database
  # NOTE: Credentials here must match DATABASE_URL in .env
  # .env: DATABASE_URL="postgresql://postgres:postgres@localhost:5432/{project_name}?schema=public"
  postgres:
    image: postgres:17-alpine
    container_name: {project_name}-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: myservice
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: {project_name}-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  postgres-data:
    driver: local
  redis-data:
    driver: local
```

## Docker Ignore (.dockerignore)

```
# Dependencies
node_modules
.pnpm-store

# Build outputs
dist
coverage
test-results

# Development files
*.md
!README.md
.env*
!.env.example
.git
.gitignore
.vscode
.idea

# Test files
**/*.spec.ts
**/*.test.ts
**/*.e2e-spec.ts
test/

# Documentation
docs/

# Misc
*.log
*.tmp
.DS_Store
Thumbs.db
```

## Vitest Configuration (vitest.config.ts)

```typescript
import { resolve } from 'path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',

    // Allow test runs with no tests (useful in CI)
    passWithNoTests: true,

    coverage: {
      provider: 'v8',
      thresholds: {
        lines: 90,
        branches: 80,
        functions: 90,
        statements: 90
      },
      exclude: [
        '**/*.spec.ts',
        '**/*.e2e-spec.ts',
        '**/dto/*.ts',
        '**/interfaces/*.ts',
        '**/types/*.ts',
        '**/index.ts',
        'dist/**',
        'coverage/**',
        'prisma/**',
        'test/**'
      ],
      reporter: ['text', 'json', 'html', 'lcov', 'cobertura']
    },

    include: [
      'src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],
    exclude: [
      'node_modules/**',
      'dist/**',
      '**/*.e2e-spec.ts'
    ],

    testTimeout: 10000,
    hookTimeout: 10000,
    teardownTimeout: 10000,

    // Thread pool configuration
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false,
        minThreads: 1,
        maxThreads: 4,
      },
    },

    // Retry flaky tests
    retry: 2,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@common': resolve(__dirname, './src/common'),
      '@config': resolve(__dirname, './src/config'),
      '@core': resolve(__dirname, './src/core'),
      '@features': resolve(__dirname, './src/features'),
      '@auth': resolve(__dirname, './src/auth'),
    },
  },
});
```
