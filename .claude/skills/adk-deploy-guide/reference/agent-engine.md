# Agent Engine Infrastructure

> For non-scaffolded projects, fetch `https://google.github.io/adk-docs/deploy/agent-engine/index.md`.

## Deployment Architecture

Agent Engine uses **source-based deployment** — no Docker container or Dockerfile. Your agent code is packaged as a base64-encoded tarball and deployed directly to the managed Vertex AI service.

> **No `gcloud` CLI exists for Agent Engine.** Deploy via `deploy.py` or `adk deploy agent_engine`. Query via the Python `vertexai.Client` SDK.

**App class:** Your agent extends `AdkApp` (from `vertexai.agent_engines.templates.adk`). Key methods:

```python
from vertexai.agent_engines.templates.adk import AdkApp

class MyAgentApp(AdkApp):
    def set_up(self):
        """Initialization — Vertex AI client, telemetry setup."""
        ...

    def register_operations(self) -> dict:
        """Declare operations exposed to Agent Engine."""
        return {"async_stream_query": [...]}

    async def async_stream_query(self, *, message: str, user_id: str, session_id: str):
        """Streaming response method — primary entry point."""
        async for event in self._runner.run_async(...):
            yield event
```

## deploy.py CLI

Scaffolded projects deploy via `uv run -m app.app_utils.deploy`. Run with `--help` for full flag reference.

**Deployment flow:**
1. `uv export` generates `.requirements.txt` from lockfile
2. `deploy.py` packages source, creates or updates the Agent Engine instance
3. Writes `deployment_metadata.json` with the engine resource ID

Deployments take **5-10 minutes**. If `make deploy` times out, check if the engine was created and manually populate `deployment_metadata.json`.

## deployment_metadata.json

Written by `deploy.py` after successful deployment:

```json
{
  "remote_agent_engine_id": "projects/PROJECT/locations/LOCATION/reasoningEngines/ENGINE_ID",
  "deployment_target": "agent_engine",
  "is_a2a": false,
  "deployment_timestamp": "2025-02-25T10:30:00.000Z"
}
```

Used by: subsequent deploys (update vs create), testing notebook, playground (`expose_app.py --mode remote`), load tests. Cloud Run does not use this file.

## Session & Artifact Services

| Service | Configuration | Notes |
|---------|--------------|-------|
| **Sessions** | `InMemorySessionService` (default) | Stateless; state lost per connection |
| **Sessions** | `VertexAiSessionService` | Native managed sessions (persistent) |
| **Artifacts** | `GcsArtifactService` | Uses `LOGS_BUCKET_NAME` env var |
| **Artifacts** | `InMemoryArtifactService` | Fallback when no bucket configured |

## Terraform Resource

Agent Engine uses `google_vertex_ai_reasoning_engine` in `deployment/terraform/service.tf`.

Key difference from Cloud Run: the `lifecycle.ignore_changes` on `source_code_spec` is critical — source code is updated by CI/CD, not Terraform.

## CI/CD Differences from Cloud Run

| Aspect | Agent Engine | Cloud Run |
|--------|-------------|-----------|
| **Build** | `uv export` → requirements file | Docker build → container image |
| **Deploy command** | `uv run -m app.app_utils.deploy` | `gcloud run deploy --image ...` |
| **Artifact** | Base64 source tarball | Container image in Artifact Registry |
| **Python version** | Fixed at 3.12 (Terraform) | Configurable in Dockerfile |
| **Load testing** | Via `expose_app.py --mode remote` bridge | Direct HTTP to Cloud Run URL |
| **Rollback** | Redeploy only — no revision rollback | `gcloud run services update-traffic` |

## Testing a Deployed Agent Engine

```python
import json
import vertexai

with open("deployment_metadata.json") as f:
    engine_id = json.load(f)["remote_agent_engine_id"]

client = vertexai.Client(location="us-central1")
agent = client.agent_engines.get(name=engine_id)

async for event in agent.async_stream_query(message="Hello!", user_id="test"):
    print(event)
```

Or run the testing notebook:
```bash
jupyter notebook notebooks/adk_app_testing.ipynb
```
