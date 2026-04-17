# Event-Driven Agent Invocations (Cloud Run)

For event-driven workloads, add custom endpoints to `fast_api_app.py`. The ADK `get_fast_api_app()` returns a standard FastAPI app — add routes to it.

**General pattern:** decode the trigger payload → run agent with an ephemeral session → return the correct response format.

> Event-driven invocations are **Cloud Run only**. Agent Engine does not support batch or event-driven processing.

## Setup (shared across all endpoints)

```python
# fast_api_app.py
import asyncio, base64, json, uuid
from fastapi import FastAPI, Request, HTTPException
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from my_agent.agent import root_agent  # ADK convention: agent.py defines root_agent

APP_NAME = "my_agent"

# Separate session service for triggers — ephemeral sessions per invocation.
_trigger_session_service = InMemorySessionService()
_trigger_runner = Runner(
    agent=root_agent, app_name=APP_NAME, session_service=_trigger_session_service,
)

app: FastAPI = get_fast_api_app(agents_dir=..., session_service_uri=...,)

async def _run_agent(message_text: str, user_id: str = "trigger") -> list:
    """Run agent with an ephemeral session, return all events."""
    session = await _trigger_session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=str(uuid.uuid4())
    )
    events = []
    async for event in _trigger_runner.run_async(
        user_id=user_id, session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=message_text)]),
    ):
        events.append(event)
    return events
```

> **Production hardening:** Add an `asyncio.Semaphore` to cap concurrent invocations. Retry with exponential backoff on 429 / RESOURCE_EXHAUSTED.

---

## Pub/Sub Push

Pub/Sub push delivers `{"message": {"data": "<base64>", "attributes": {...}}, "subscription": "..."}`. Return 200 to ack, non-200 to nack and trigger retry.

```python
@app.post(f"/apps/{APP_NAME}/trigger/pubsub")
async def trigger_pubsub(request: Request):
    body = await request.json()
    msg = body.get("message", {})
    raw = msg.get("data", "")
    text = base64.b64decode(raw).decode("utf-8") if raw else json.dumps(msg.get("attributes", {}))

    try:
        await _run_agent(text, user_id=body.get("subscription", "pubsub"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}
```

**Terraform — Pub/Sub push subscription:**

```hcl
resource "google_pubsub_subscription" "trigger" {
  topic = google_pubsub_topic.my_topic.id
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.app.uri}/apps/my_agent/trigger/pubsub"
    oidc_token {
      service_account_email = google_service_account.app_sa.email
      audience              = google_cloud_run_v2_service.app.uri
    }
  }
  ack_deadline_seconds = 30
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "60s"
  }
}

# Allow Pub/Sub service agent to generate OIDC tokens
resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.app_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
```

---

## Eventarc

Binary mode (default): `ce-*` headers + Pub/Sub message body. Structured mode: full JSON with `data` key.

```python
@app.post(f"/apps/{APP_NAME}/trigger/eventarc")
async def trigger_eventarc(request: Request):
    body = await request.json()
    if "message" in body and body["message"].get("data"):
        text = base64.b64decode(body["message"]["data"]).decode("utf-8")
    elif "data" in body:
        text = json.dumps(body["data"])
    else:
        text = json.dumps(body)

    source = body.get("source") or request.headers.get("ce-source", "eventarc")
    try:
        await _run_agent(text, user_id=source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}
```

**Terraform — Eventarc trigger (Cloud Storage):**

```hcl
resource "google_eventarc_trigger" "storage_trigger" {
  name     = "${var.project_name}-storage-trigger"
  location = var.region
  project  = var.dev_project_id

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.uploads.name
  }

  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.app.name
      region  = var.region
      path    = "/apps/my_agent/trigger/eventarc"
    }
  }

  service_account = google_service_account.app_sa.email
}
```

---

## BigQuery Remote Function

BQ sends `{"calls": [["row1"], ...], "caller": "..."}`, expects `{"replies": ["...", ...]}` in the same row order. BQ **cannot use URL paths** — register at `POST /`.

```python
@app.post("/")
async def trigger_bq(request: Request):
    body = await request.json()
    calls: list = body.get("calls", [])
    user_id = body.get("caller") or body.get("sessionUser") or "bq"

    async def _process_row(row_args: list) -> str:
        text = row_args[0] if (len(row_args) == 1 and isinstance(row_args[0], str)) \
               else json.dumps(row_args)
        try:
            events = await _run_agent(text, user_id=user_id)
            return json.dumps([e.model_dump(mode="json") for e in events])
        except Exception as e:
            return f"Error: {e}"

    replies = await asyncio.gather(*[_process_row(row) for row in calls])
    return {"replies": list(replies)}
```

**Terraform — BigQuery remote function:**

```hcl
resource "google_bigquery_routine" "my_fn" {
  routine_type    = "SCALAR_FUNCTION"
  language        = "SQL"
  definition_body = ""
  arguments {
    name          = "message"
    argument_kind = "FIXED_TYPE"
    data_type     = jsonencode({ typeKind = "STRING" })
  }
  return_type = jsonencode({ typeKind = "STRING" })
  remote_function_options {
    endpoint   = google_cloud_run_v2_service.app.uri  # root URL only — BQ cannot use paths
    connection = google_bigquery_connection.my_conn.name
  }
}
```
