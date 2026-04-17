# Evaluation Criteria Reference

## All 8 Criteria

| Criterion | What it evaluates | Needs reference data? |
|-----------|------------------|----------------------|
| `tool_trajectory_avg_score` | Did the agent call the right tools in the right order? | Yes — provide `tool_uses` in evalset |
| `response_match_score` | Does the final response match expected text? (lexical) | Yes |
| `final_response_match_v2` | Does the final response match expected meaning? (LLM judge) | Yes |
| `rubric_based_final_response_quality_v1` | Is the final response high quality? (custom rubrics) | No — define rubrics |
| `rubric_based_tool_use_quality_v1` | Did the agent use tools well? (custom rubrics) | No — define rubrics |
| `hallucinations_v1` | Is the response grounded / not hallucinating? | No |
| `safety_v1` | Is the response safe and harmless? | No |
| `per_turn_user_simulator_quality_v1` | Is the user simulator following the conversation plan? | No |

Default when no config provided: `tool_trajectory_avg_score: 1.0` + `response_match_score: 0.8`

---

## Trajectory Match Types

`tool_trajectory_avg_score` supports three match types:

| Match Type | Behavior | When to Use |
|------------|----------|-------------|
| `EXACT` (default) | Agent must call exactly the tools listed, in exact order, no extras | Regression testing, strict workflow validation |
| `IN_ORDER` | Expected tools must appear in sequence; extra tool calls between them are allowed | Key actions must happen in order, but model may do extra work |
| `ANY_ORDER` | All expected tools must be called; order doesn't matter | Non-sequential workflows where all tools must fire |

**Proactivity Trajectory Gap:** LLMs often call extra tools not in the evalset (e.g., an extra `google_search`). `EXACT` match fails in this case. Prefer `IN_ORDER` for most evals unless you specifically need strict regression checks.

---

## Judge Model Configuration

All LLM-as-judge criteria accept `judge_model_options`:

```json
{
  "judge_model_options": {
    "judge_model": "gemini-3.1-flash",
    "num_samples": 5
  }
}
```

- `judge_model` — model used to score responses
- `num_samples` — number of independent scoring samples; final score is majority vote. Default: 5. Higher values reduce LLM variance.

---

## Rubric and Hallucination Scoring

**Rubric scoring:** Each rubric returns yes (1.0) or no (0.0). Overall score = average across all rubrics and all invocations. Example rubric config:

```json
{
  "rubric_based_final_response_quality_v1": {
    "threshold": 0.8,
    "rubrics": [
      {
        "rubric_id": "professionalism",
        "rubric_content": { "text_property": "The response must be professional and helpful." }
      },
      {
        "rubric_id": "no_unconfirmed_booking",
        "rubric_content": { "text_property": "The agent must NEVER book without asking for confirmation." }
      }
    ]
  }
}
```

**Hallucination scoring:** Response is segmented into sentences, each labeled `supported`, `unsupported`, `contradictory`, `disputed`, or `not_applicable`. Score = percentage of `supported` + `not_applicable` sentences. A score of 1.0 means every factual claim is grounded in tool output.

---

## Full Configuration Example

```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "match_type": "IN_ORDER"
    },
    "final_response_match_v2": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-3.1-flash",
        "num_samples": 5
      }
    },
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.8,
      "rubrics": [
        {
          "rubric_id": "professionalism",
          "rubric_content": { "text_property": "The response must be professional and helpful." }
        }
      ]
    },
    "hallucinations_v1": {
      "threshold": 0.8
    }
  }
}
```

Simple threshold shorthand is also valid: `"response_match_score": 0.8`

Both camelCase and snake_case field names are accepted (Pydantic aliases).

---

## Custom Metrics

Register a custom metric function in `eval_config.json`:

```json
{
  "criteria": {
    "my_custom_metric": 0.8
  },
  "custom_metrics": {
    "my_custom_metric": {
      "code_config": {
        "name": "my_app.eval.my_module.my_metric_function"
      },
      "description": "Evaluates something built-in metrics cannot"
    }
  }
}
```

Custom metric functions receive full `Invocation` objects including all multimodal parts. See `multimodal-eval.md` for a complete implementation example.

---

## Deep Dive

- Fetch `https://google.github.io/adk-docs/evaluate/criteria/index.md` for complete config examples and the custom metrics API.
