# Evaluating Agents with `google_search` and Built-in Tools

## google_search Behavior — Critical

`google_search` is NOT a regular tool — it is a **model-internal grounding feature**.

**Key behavior:**
- Custom tools (`save_preferences`, `book_flight`, etc.) → appear as `function_call` in trajectory
- `google_search` → NEVER appears in trajectory (happens inside the model)

Search results come back as `grounding_metadata`, not function call/response events. Despite this, the evaluator still detects it at the session level and raises:

```json
{
  "error_code": "UNEXPECTED_TOOL_CALL",
  "error_message": "Unexpected tool call: google_search"
}
```

This causes `tool_trajectory_avg_score` to ALWAYS fail for agents using `google_search`.

---

## Metric Compatibility for `google_search` Agents

| Metric | Usable? | Why |
|--------|---------|-----|
| `tool_trajectory_avg_score` | NO | Always fails due to unexpected google_search detection |
| `rubric_based_final_response_quality_v1` | YES | Evaluates output quality semantically via LLM judge |
| `rubric_based_tool_use_quality_v1` | YES | Evaluates tool usage reasoning via LLM judge |
| `final_response_match_v2` | Maybe | Works if expected outputs are stable enough |
| `hallucinations_v1` | YES | Checks response is grounded in source material |

---

## Evalset Best Practices for `google_search` Agents

Do NOT include `google_search` in `intermediate_data.tool_uses` — it will never match:

```json
{
  "eval_id": "news_digest_test",
  "conversation": [{
    "user_content": { "parts": [{"text": "Give me my news digest."}] }
  }]
}
```

For agents mixing `google_search` with custom tools, include only the custom tools:

```json
{
  "intermediate_data": {
    "tool_uses": [
      { "name": "save_feedback" }
    ]
  }
}
```

Config for `google_search` agents — remove trajectory metric entirely and use rubric-based:

```json
{
  "criteria": {
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.6,
      "rubrics": [
        { "rubric_id": "has_citations", "rubric_content": { "text_property": "Response includes source citations or references" } },
        { "rubric_id": "relevance", "rubric_content": { "text_property": "Response directly addresses the user's query" } }
      ]
    }
  }
}
```

---

## ADK Built-in Tools: Trajectory Behavior Reference

**Model-Internal Tools — do NOT appear in trajectory:**

| Tool | In Trajectory? | Eval Strategy |
|------|:-:|--------------|
| `google_search` | No | Rubric-based |
| `google_search_retrieval` | No | Rubric-based |
| `BuiltInCodeExecutor` | No | Check output content |
| `VertexAiSearchTool` | No | Rubric-based |
| `url_context` | No | Rubric-based |

These inject into `llm_request.config.tools` as model capabilities, not as callable Python functions.

**Function-Based Tools — DO appear in trajectory:**

| Tool | In Trajectory? | Eval Strategy |
|------|:-:|--------------|
| `load_web_page` | Yes | `tool_trajectory_avg_score` works |
| Custom Python functions | Yes | `tool_trajectory_avg_score` works |
| `AgentTool` | Yes | `tool_trajectory_avg_score` works |

**Rule of thumb:** If the tool provides grounding, retrieval, or code execution built into Gemini — it's model-internal and won't appear in trajectory. If it's a Python function you wrote — it appears in trajectory.

**When mixing both types** (e.g., `google_search` + `save_preferences`):
- Remove `tool_trajectory_avg_score` entirely, OR
- Include only the function-based tools in `tool_uses` and accept the trajectory will be incomplete

---

## Mock Mode for External APIs

When your agent calls external APIs, add mock mode so evals run without real credentials:

```python
def call_external_api(query: str) -> dict:
    api_key = os.environ.get("EXTERNAL_API_KEY", "")
    if not api_key or api_key == "dummy_key":
        return {"status": "success", "data": "mock_response"}
    # Real API call here
    ...
```

Set `EXTERNAL_API_KEY=dummy_key` in your eval environment. This keeps eval runs deterministic and credential-free.
