````markdown
# Dockerfiles — All Stacks

Copy-ready multi-stage Dockerfiles and .dockerignore for all backend stacks. Every pattern follows: multi-stage build, non-root user (UID 1001), HEALTHCHECK, minimal runtime image.

---

## NestJS 11.x / Node 24 (pnpm + Prisma)

```dockerfile
# my-service — Multi-Stage Production Dockerfile (NestJS 11.x / Node 24)

# ============================================
# Stage 1: Base — node:24-alpine + pnpm + non-root user
# ============================================
FROM node:24-alpine AS base
RUN corepack enable && corepack prepare pnpm@latest --activate
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nestjs

# ============================================
# Stage 2: Dependencies — layer cache for pnpm installs
# ============================================
FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
COPY prisma ./prisma/
RUN pnpm install --frozen-lockfile

# ============================================
# Stage 3: Builder — TypeScript compile + Prisma client + prune
# ============================================
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm prisma generate
RUN pnpm build
RUN pnpm prune --prod

# ============================================
# Stage 4: Runner — minimal production image
# ============================================
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
USER nestjs
COPY --from=builder --chown=nestjs:nodejs /app/dist ./dist
COPY --from=builder --chown=nestjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nestjs:nodejs /app/package.json ./
COPY --from=builder --chown=nestjs:nodejs /app/prisma ./prisma
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health/live || exit 1
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

**.dockerignore (NestJS):**
```
node_modules
.pnpm-store
dist
coverage
test-results
*.md
!README.md
.env*
!.env.example
.git
.gitignore
.vscode
.idea
**/*.spec.ts
**/*.test.ts
**/*.e2e-spec.ts
test/
docs/
*.log
*.tmp
.DS_Store
```

---

## Spring Boot WebFlux 3.5.x / Java 21

```dockerfile
# my-service — Multi-Stage Production Dockerfile (Spring Boot WebFlux 3.5.x / Java 21)

# ============================================
# Stage 1: Build — Maven + JDK 21 (full build environment)
# ============================================
FROM maven:3.9-eclipse-temurin-21-alpine AS build

WORKDIR /app

# Copy POM first for Maven dependency cache layer
COPY pom.xml .
RUN --mount=type=cache,target=/root/.m2 \
    mvn dependency:go-offline -q

# Copy source and build (skip tests — run separately in CI)
COPY src ./src
RUN --mount=type=cache,target=/root/.m2 \
    mvn package -DskipTests -q

# ============================================
# Stage 2: Runtime — JRE only (no JDK, no Maven, no build tools)
# ============================================
FROM eclipse-temurin:21-jre-alpine

# Security: non-root user
RUN addgroup -g 1001 -S spring && \
    adduser -S spring -u 1001 -G spring

WORKDIR /app

# Copy only the application JAR
COPY --from=build --chown=spring:spring /app/target/*.jar app.jar

USER 1001

EXPOSE 8080

# Health check via Spring Actuator — allow 40s startup for JVM + Flyway migrations
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget -q --spider http://localhost:8080/actuator/health || exit 1

# JVM tuning: container-aware heap (75% of limit), secure random, active profile from env
ENTRYPOINT ["java", \
  "-XX:+UseContainerSupport", \
  "-XX:MaxRAMPercentage=75.0", \
  "-Djava.security.egd=file:/dev/./urandom", \
  "-jar", "app.jar"]
```

**.dockerignore (Spring Boot):**
```
target/
.git
.gitignore
.mvn
*.md
!README.md
.env*
!.env.example
.vscode
.idea
*.iml
src/test/
docs/
*.log
.DS_Store
```

**Note:** `SPRING_PROFILES_ACTIVE` is passed as an environment variable in docker-compose or Cloud Run — not baked into the image.

---

## Python FastAPI 3.14 (uv — multi-stage)

```dockerfile
# my-service — Multi-Stage Production Dockerfile (Python FastAPI 3.14 / uv)

# ============================================
# Stage 1: Builder — install production dependencies
# ============================================
FROM python:3.14-slim AS builder

WORKDIR /app

# Install uv for fast, reproducible dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first — layer cache preserved on code-only changes
COPY pyproject.toml uv.lock* ./

# Install production dependencies only into .venv
RUN uv sync --no-dev --frozen

# Copy application source
COPY src/ src/

# ============================================
# Stage 2: Runtime — minimal Python slim, no build tools
# ============================================
FROM python:3.14-slim AS runtime

# Security: non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy virtual env and source from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

EXPOSE 8000

USER appuser

CMD ["uvicorn", "my_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**.dockerignore (Python):**
```
.venv
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.mypy_cache
.ruff_cache
htmlcov
.coverage
dist
build
*.egg-info
.git
.gitignore
.env*
!.env.example
.vscode
.idea
tests/
docs/
*.md
!README.md
*.log
.DS_Store
```

---

## Python Agentic AI (uv + gunicorn workers)

```dockerfile
# my-agent-service — Multi-Stage Production Dockerfile (Python 3.14 / LangGraph / gunicorn)

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.14-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen

COPY src/ src/

# ============================================
# Stage 2: Runtime — gunicorn + uvicorn workers
# ============================================
FROM python:3.14-slim AS runtime

RUN groupadd -r agent && useradd -r -g agent agent

WORKDIR /app

COPY --from=builder --chown=agent:agent /app/.venv /app/.venv
COPY --from=builder --chown=agent:agent /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health').raise_for_status()"

EXPOSE 8000

USER agent

# gunicorn + uvicorn workers: 4 workers, 120s timeout, graceful shutdown 30s
CMD ["gunicorn", "my_agent_service.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-"]
```

---

## TypeScript / Fastify / Node 24

```dockerfile
# my-service — Multi-Stage Production Dockerfile (TypeScript/Fastify / Node 24)

# ============================================
# Stage 1: Production dependencies
# ============================================
FROM node:24-alpine AS deps

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nodeapp

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# ============================================
# Stage 2: Builder — TypeScript compile
# ============================================
FROM node:24-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ============================================
# Stage 3: Production Runner
# ============================================
FROM node:24-alpine AS runner

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nodeapp

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
USER nodeapp

COPY --from=deps --chown=nodeapp:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nodeapp:nodejs /app/dist ./dist
COPY --from=builder --chown=nodeapp:nodejs /app/package.json ./

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "dist/index.js"]
```

**.dockerignore (TypeScript/Node):**
```
node_modules
dist
coverage
.git
.gitignore
.env*
!.env.example
*.md
!README.md
.vscode
.idea
**/*.spec.ts
**/*.test.ts
test/
docs/
*.log
.DS_Store
```
````
