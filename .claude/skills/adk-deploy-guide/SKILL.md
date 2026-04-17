---
name: adk-deploy-guide
description: "MUST READ before deploying any ADK agent to Google Cloud — covers Cloud Run, Agent Engine, Vertex AI, event-driven agents, and ADK CI/CD pipelines. Use when deploying ADK agents to production, not for agent code patterns (use google-adk) or project scaffolding."
allowed-tools: Bash, Read, Write, Edit
metadata:
  triggers: deploy ADK agent, Cloud Run, Agent Engine, Vertex AI deployment, ADK production, ADK CI/CD
  related-skills: google-adk, agentic-ai-dev, python-dev
  domain: infrastructure
  role: specialist
  scope: deployment
  output-format: code
last-reviewed: "2026-03-15"
---

# ADK Deployment Guide

> **Scaffolded project?** Use `make` commands — they wrap Terraform, Docker, and deployment.
>
> **No scaffold?** See [Quick Deploy](#quick-deploy-adk-cli) below. For production infrastructure, see the `/scaffold-adk` command or load the `architecture-design` skill for infrastructure planning.

## Iron Law

**NEVER create GCP resources manually via `gcloud` for production. Define all infrastructure in Terraform.**
Exception: quick experimentation only — console or `gcloud` for throwaway resources is fine.

---

## Reference Files

| File | Contents |
|------|----------|
| `reference/agent-engine.md` | AdkApp pattern, deploy.py CLI, session/artifact services, CI/CD differences |
| `reference/cloud-run.md` | Dockerfile, session types, scaling defaults, networking, ingress, IAP |
| `reference/event-driven.md` | Pub/Sub, Eventarc, BigQuery Remote Function trigger patterns |
| `reference/terraform-patterns.md` | Custom resources, IAM bindings, state management, importing resources |

For agent code patterns and testing strategies, see `google-adk` skill. For evaluations and observability, see `adk-eval-guide` and `adk-observability-guide` skills.

---

## Deployment Target Decision Matrix

| Criteria | Agent Engine | Cloud Run |
|----------|-------------|-----------|
| **Deployment** | Source-based, no Docker | Dockerfile + container image |
| **Scaling** | Managed auto-scaling | Fully configurable (min/max instances) |
| **Session state** | Native `VertexAiSessionService` | In-memory (dev), Cloud SQL, or Agent Engine backend |
| **Event-driven** | Not supported | Pub/Sub, Eventarc, BigQuery Remote Function via `/invoke` |
| **Cost model** | vCPU-hours + memory-hours (not billed when idle) | Per-instance-second + min instance costs |
| **Setup complexity** | Lower — managed, purpose-built for agents | Medium — Dockerfile, Terraform, networking |
| **Best for** | Minimal ops, managed infrastructure | Event-driven workloads, full infrastructure control |

Ask the user which target fits their needs before proceeding.

---

## Quick Deploy (ADK CLI)

No Makefile, Terraform, or Dockerfile required.

```bash
# Cloud Run
adk deploy cloud_run --project=PROJECT --region=REGION path/to/agent/

# Agent Engine
adk deploy agent_engine --project=PROJECT --region=REGION path/to/agent/
```

Both support `--with_ui` to deploy the ADK dev UI. Cloud Run accepts extra `gcloud` flags after `--`.

---

## Process

1. **Gather requirements** — target (Agent Engine vs Cloud Run), project ID, region, secrets needed
2. **Choose target** — use the decision matrix above; ask if unclear
3. **Scaffold or write Terraform** — run `/scaffold-adk` or manually write `deployment/terraform/`
4. **Configure secrets** — use Secret Manager, not env vars, for API keys and credentials
5. **Deploy** — `make deploy` (scaffolded) or `adk deploy <target>` (CLI)
6. **Verify** — health check endpoint, test with curl or testing notebook, run load tests

---

## Secret Manager

```bash
# Create
echo -n "YOUR_API_KEY" | gcloud secrets create MY_SECRET_NAME --data-file=-

# Update
echo -n "NEW_KEY" | gcloud secrets versions add MY_SECRET_NAME --data-file=-

# Agent Engine: pass at deploy time
make deploy SECRETS="API_KEY=my-api-key,DB_PASS=db-password:2"
```

Grant `secretmanager.secretAccessor` to `app_sa` (Cloud Run) or `service-PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com` (Agent Engine).

---

## Documentation Sources

| Source | URL | Purpose |
|--------|-----|---------|
| ADK Deployment | `https://google.github.io/adk-docs/deploy/` | Official deployment docs |
| Cloud Run | `https://google.github.io/adk-docs/deploy/cloud-run/index.md` | Cloud Run specifics |
| Agent Engine | `https://google.github.io/adk-docs/deploy/agent-engine/index.md` | Agent Engine specifics |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Agent Engine deploy timeout | Check if engine was created; manually populate `deployment_metadata.json` |
| 403 on deploy | `cicd_runner_sa` missing deployment role or SA impersonation in target project |
| 403 testing Cloud Run | Add `Authorization: Bearer $(gcloud auth print-identity-token)` header |
| Secret access denied | Verify `secretAccessor` granted to `app_sa`, not default compute SA |
| Cold starts slow | Set `min_instance_count > 0` in Cloud Run Terraform config |
| Resource already exists | Use `terraform import` — see `reference/terraform-patterns.md` |
