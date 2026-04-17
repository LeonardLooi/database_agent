---
name: deployment-ci-cd
description: CI/CD pipeline design and deployment automation for all stacks — GitHub Actions workflows, Docker multi-stage builds, Cloud Run deployments, Flutter distribution, and Firebase rule deployments. Use when setting up or reviewing CI/CD pipelines, deployment workflows, or automated release processes.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
agent: deployment-engineer
context: fork
metadata:
  triggers: CI/CD, github actions, deploy, pipeline, cloud run deploy, firebase deploy, flutter build pipeline, docker build, deployment workflow, automated release
  related-skills: docker, gcp-cloud-run, terraform-skill, flutter-mobile
  domain: infrastructure
  role: specialist
  scope: implementation
  output-format: implementation
last-reviewed: "2026-03-29"
---

**Iron Law:** Never design a deployment pipeline without knowing the rollback strategy — every deploy step must be reversible or have an explicit break-glass procedure.

# Deployment CI/CD

CI/CD pipeline design and deployment automation specialist covering GitHub Actions, Docker, Cloud Run, Flutter mobile distribution, and Firebase deployments.

## When to Use

- Setting up a new GitHub Actions CI/CD pipeline
- Reviewing an existing deployment workflow
- Designing Docker multi-stage build optimization
- Setting up Cloud Run progressive delivery (traffic splitting)
- Automating Flutter builds and distribution to Firebase App Distribution
- Configuring Firebase Hosting, Firestore rules, or Functions deployment

## Pipeline Patterns by Stack

| Stack | Build | Test | Deploy |
|-------|-------|------|--------|
| **NestJS** | Docker multi-stage | Vitest | Cloud Run (canary → prod) |
| **Spring Boot** | Maven + Docker | JUnit | Cloud Run (health check gate) |
| **Python/FastAPI** | Docker + uv | pytest | Cloud Run Functions |
| **Angular** | `ng build --prod` | Karma/Jest | Firebase Hosting |
| **Flutter** | `flutter build apk/ipa` | `flutter test` | Firebase App Distribution / App Store |

## Key Principles

- **Multi-stage Docker**: separate build and runtime stages; never ship dev dependencies
- **Health check gate**: Cloud Run deploy must pass health check before traffic shift
- **Secret management**: use Workload Identity Federation (not service account keys)
- **Progressive delivery**: canary → 10% → 50% → 100% with automated rollback on error rate spike
- **Container scanning**: Trivy scan before push to Artifact Registry

## Process

1. Identify target stack and deployment environment
2. Load `docker` skill for Dockerfile patterns (if containerizing)
3. Load `gcp-cloud-run` skill for Cloud Run-specific patterns (if deploying to GCP)
4. Design pipeline stages: build → test → security scan → push → deploy → verify
5. Define rollback strategy for each stage
6. Output GitHub Actions workflow YAML + deployment configuration

## Production Readiness Checklist

Before any production deploy, verify ALL of the following. If any item is NO → do not deploy.

### Application
- [ ] `/health` endpoint responds 200 with DB connectivity check (see `reference/health-endpoints.md`)
- [ ] All required env vars validated at startup — app fails fast if missing (see `reference/env-config-validation.md`)
- [ ] No secrets hardcoded in source code or committed config files
- [ ] `.env.example` committed with all keys, placeholder values only
- [ ] Error handling: all catch blocks log + rethrow or return error state (no silent failures)

### Container / Docker
- [ ] Multi-stage Dockerfile — dev deps not in production image
- [ ] Non-root user in Dockerfile (`USER appuser`)
- [ ] Specific image tags pinned — no `:latest`
- [ ] HEALTHCHECK instruction in Dockerfile
- [ ] `.dockerignore` excludes: `node_modules`, `.git`, `.env`, `dist`, `coverage`
- [ ] `docker scout` or `trivy image` scan — zero CRITICAL CVEs

### CI/CD Pipeline
- [ ] Tests pass (all: unit + integration)
- [ ] Linting + type-check pass (zero errors)
- [ ] Container image pushed to Artifact Registry with commit SHA tag
- [ ] Health check gate passes before any traffic shift
- [ ] Rollback strategy defined and tested for this deploy

### Cloud Run (GCP Stack)
- [ ] Workload Identity Federation configured — no service account key files
- [ ] Deploy uses `--no-traffic` first → canary 10% → verify → 100%
- [ ] Memory limits set (`--memory` flag matches actual service requirements)
- [ ] Concurrency configured (`--concurrency` — default 80, tune per service)
- [ ] Min instances = 0 for cost (or 1+ for latency-sensitive services)

### Security
- [ ] `security-reviewer` agent verdict: no CRITICAL or HIGH findings
- [ ] All API endpoints require authentication (no accidental public exposure)
- [ ] CORS policy explicitly configured (not wildcard `*` in production)
- [ ] Secrets stored in Secret Manager, not Cloud Run env vars directly

### Post-Deploy Verification
- [ ] Health endpoint returns 200 on new revision URL
- [ ] Smoke test: critical user flow works end-to-end
- [ ] Error rate < 0.1% for 5 minutes post-deploy
- [ ] Rollback procedure verified working (test once per quarter)
