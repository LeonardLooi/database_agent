# REST API Intent Connector

**Date:** 2026-05-13
**Branch:** claude/update-documentation-CWKWj

## Overview

Added support for a `rest` connector type in the intent YAML. When a user message matches an intent backed by a REST connector, the backend POSTs the original prompt to the configured endpoint and returns the API response through the existing agent loop to the UI.

## Runtime Flow

```
User message
  └─► QueryRouter detects keyword → data query
        └─► estimate_intent() matches REST-backed intent
              └─► LLM agent loop starts
                    └─► LLM calls call_rest_api(intent_name, prompt)
                          └─► _dispatch_rest_api resolves URL/method/headers from YAML
                                └─► POST {"prompt": "<user message>"} → REST API
                                      └─► Response returned → LLM narrates → UI displays
```

The LLM receives `intent_name` and `prompt` only. URL, method, and auth headers are resolved server-side from the YAML — they never travel through the LLM prompt.

## Files Changed

### New

| File | Purpose |
|---|---|
| `app/agent/connectors/rest_connector.py` | Async httpx client. Sends `{"prompt": "..."}` as POST body. Resolves `${ENV_VAR}` references in header values at call time. |

### Modified

| File | What changed |
|---|---|
| `app/agent/intent_loader.py` | Added `"rest"` to `ConnectorConfig.type` Literal. Added `url: str`, `method: str`, `headers: dict` fields. |
| `app/agent/tools/query_tools.py` | Added `call_rest_api()` function. `RestConnector` imported at module top. |
| `app/agent/shared_toolkit.py` | Registered `call_rest_api` in `_TOOL_SCHEMAS`, `dispatch()`, `get_adk_functions()`, `get_strands_tools()`. Added `_dispatch_rest_api()` helper for server-side intent resolution. Updated `intents_as_system_context()` to instruct the LLM to use `call_rest_api` for REST connectors. |
| `config/intents/sample_intents.yaml` | Added `ai_insights` sample intent demonstrating the REST connector shape. |

### Tests

| File | Tests added |
|---|---|
| `tests/test_connectors.py` | 4 tests for `RestConnector` (POST JSON, POST plain text, GET query param, HTTP error propagation). 3 tests for `_resolve_env_vars` (known var, unknown var, empty). |
| `tests/test_query_tools.py` | 3 tests for `call_rest_api` (success JSON, custom label, HTTP error propagation). |
| `tests/test_shared_toolkit.py` | Updated expected tool set to include `call_rest_api`. |

## YAML Schema

```yaml
intents:
  - name: ai_insights
    description: "Ask the AI insights service a free-form question about business data"
    connectors:
      - type: rest
        url: "https://your-api.example.com/endpoint"
        method: POST                          # GET | POST | PUT | PATCH
        headers:
          Authorization: "Bearer ${API_TOKEN}"  # resolved from env at call time
          Content-Type: "application/json"
    keywords:
      - insights
      - analyse
```

## Request / Response Contract

**Request body** (always POST):
```json
{ "prompt": "<user's verbatim message>" }
```

**Expected response** — any valid JSON or plain text:
```json
{ "answer": "...", "data": { ... } }
```
The LLM receives the full response and composes a natural language reply for the UI.

## Environment Variables

Auth tokens in `headers` use `${VAR_NAME}` syntax and are resolved from the process environment at call time. Set them in your `.env` / container config before starting the backend.

Example for the sample intent:
```
INSIGHTS_API_TOKEN=your-token-here
```

## Design Decisions

- **LLM never sees the URL** — intent resolution is server-side only, preventing prompt injection via hallucinated endpoints.
- **No new response formatter** — the REST JSON arrives as a tool result; the LLM narrates it as natural language, using the same path as all other agent loop responses.
- **Headers resolved at call time** — not at load time — so rotating a token requires only an env var change, not a restart.
- **`RestConnector` is not a subclass of `BaseConnector`** — `BaseConnector` is sync and DataFrame-oriented; REST responses are async and unstructured JSON.
