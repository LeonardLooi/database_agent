# Prompt Optimization

> Referenced by `prompt-engineering-patterns` SKILL.md. Covers systematic refinement, A/B testing, token reduction, versioning, and production metrics.

## Optimization Process

```
1. Establish baseline (accuracy, tokens, latency, success rate)
2. Identify failure category (format, factual, logic, incomplete, hallucination)
3. Apply one change at a time
4. Test on representative sample (min 20 inputs)
5. Measure all metrics (not just accuracy)
6. Accept change only if improvement is statistically significant
7. Version and document
```

---

## Failure Categories

Before optimizing, classify what's failing:

| Category | Description | Fix |
|----------|-------------|-----|
| Format failures | Wrong output structure | Add explicit format with example |
| Factual errors | Hallucinated facts | Add "only use provided context" constraint |
| Logic errors | Wrong reasoning | Add CoT / verification step |
| Incomplete | Cuts off mid-response | Reduce prompt size or increase max_tokens |
| Off-topic | Drifts from task | Strengthen role definition + hard constraints |
| Inconsistent | Different output each run | Add few-shot examples, reduce temperature |

---

## A/B Testing Framework

```python
import statistics
import time
from dataclasses import dataclass

@dataclass
class PromptTestResult:
    prompt_id: str
    accuracy: float
    avg_tokens: float
    avg_latency_ms: float
    success_rate: float
    sample_size: int


def evaluate_prompt(prompt: str, test_cases: list[dict], llm) -> PromptTestResult:
    """Evaluate a prompt against a test suite."""
    results = []

    for case in test_cases:
        start = time.time()
        response = llm.invoke(prompt.format(**case["inputs"]))
        latency = (time.time() - start) * 1000

        correct = case["expected"] in response.content
        results.append({
            "correct": correct,
            "tokens": response.usage_metadata.get("total_tokens", 0),
            "latency_ms": latency,
            "success": not response.content.startswith("I cannot")
        })

    return PromptTestResult(
        prompt_id=prompt[:40],
        accuracy=sum(r["correct"] for r in results) / len(results),
        avg_tokens=statistics.mean(r["tokens"] for r in results),
        avg_latency_ms=statistics.mean(r["latency_ms"] for r in results),
        success_rate=sum(r["success"] for r in results) / len(results),
        sample_size=len(results)
    )


def ab_test(prompt_a: str, prompt_b: str, test_cases: list[dict], llm) -> dict:
    """Compare two prompt variants."""
    result_a = evaluate_prompt(prompt_a, test_cases, llm)
    result_b = evaluate_prompt(prompt_b, test_cases, llm)

    winner = "A" if result_a.accuracy > result_b.accuracy else "B"
    token_delta = result_b.avg_tokens - result_a.avg_tokens
    accuracy_delta = result_b.accuracy - result_a.accuracy

    return {
        "winner": winner,
        "accuracy_delta": f"{accuracy_delta:+.1%}",
        "token_delta": f"{token_delta:+.0f} tokens/request",
        "latency_delta": f"{result_b.avg_latency_ms - result_a.avg_latency_ms:+.0f}ms",
        "result_a": result_a,
        "result_b": result_b
    }
```

---

## Token Reduction Techniques

```python
# BEFORE: verbose, redundant
verbose_prompt = """
Please carefully analyze the following code that has been provided to you.
Your task is to review the code thoroughly and identify any issues, bugs,
problems, or potential improvements that you think would be helpful.
Please make sure to look at everything carefully.
Code: {code}
"""

# AFTER: concise, same quality
concise_prompt = """Review this code for bugs, security issues, and improvements.
Code: {code}
Output: Issues (severity, line, description), Fixes (code diff)"""

# Savings: ~60 tokens -> ~20 tokens per request = 66% reduction
```

**Reduction checklist:**
- [ ] Remove filler phrases ("Please", "carefully", "make sure to")
- [ ] Consolidate repeated instructions into one
- [ ] Move static content to system prompt (cached, not repeated)
- [ ] Use abbreviations consistently (after first definition)
- [ ] Replace paragraphs with bullet lists

---

## Prompt Versioning

Treat prompts as code — semantic versioning, changelog, rollback.

```python
from datetime import datetime
import json
from pathlib import Path


class PromptVersionControl:
    def __init__(self, storage_path: str = "prompts/versions"):
        self.path = Path(storage_path)
        self.path.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        name: str,
        prompt: str,
        version: str,
        metrics: dict,
        notes: str = ""
    ) -> None:
        """Save a prompt version with its performance metrics."""
        record = {
            "name": name,
            "version": version,
            "prompt": prompt,
            "metrics": metrics,
            "notes": notes,
            "saved_at": datetime.utcnow().isoformat()
        }
        file = self.path / f"{name}_v{version}.json"
        file.write_text(json.dumps(record, indent=2))

    def rollback(self, name: str, version: str) -> str:
        """Retrieve a previous prompt version."""
        file = self.path / f"{name}_v{version}.json"
        return json.loads(file.read_text())["prompt"]

    def compare(self, name: str, version_a: str, version_b: str) -> dict:
        """Compare metrics between two versions."""
        a = json.loads((self.path / f"{name}_v{version_a}.json").read_text())
        b = json.loads((self.path / f"{name}_v{version_b}.json").read_text())
        return {
            "accuracy": f"{b['metrics']['accuracy'] - a['metrics']['accuracy']:+.1%}",
            "tokens": f"{b['metrics']['avg_tokens'] - a['metrics']['avg_tokens']:+.0f}",
        }


# Usage
pvc = PromptVersionControl()
pvc.save(
    name="sql_classifier",
    prompt=OPTIMIZED_PROMPT,
    version="1.2.0",
    metrics={"accuracy": 0.94, "avg_tokens": 320, "latency_ms": 450},
    notes="Added edge case examples for ambiguous queries"
)
```

---

## Production Metrics to Track

```python
# Track these per prompt in production
PROMPT_METRICS = {
    "accuracy": "% outputs matching expected (requires labeling)",
    "success_rate": "% outputs that are non-error, non-refusal",
    "avg_tokens_input": "average input token count",
    "avg_tokens_output": "average output token count",
    "latency_p50": "median response time in ms",
    "latency_p95": "95th percentile latency in ms",
    "cost_per_1k_requests": "total LLM cost per 1000 calls"
}
```

---

## Common Optimization Patterns

| Pattern | When | Before | After |
|---------|------|--------|-------|
| Add structure | Format inconsistent | "Analyze the bug" | "Output: Bug (line, description), Root Cause, Fix (code)" |
| Add examples | Format wrong | Description of format | 1-2 concrete examples |
| Add constraints | Off-topic responses | No boundaries | "ONLY answer questions about [domain]" |
| Add verification | Logic errors | Single pass | "After answering, verify your answer against..." |
| Split prompt | Too many tasks | One long instruction | Separate prompts per node/agent |

---

## Prompt Problem Diagnosis

Before optimizing a prompt, identify the failure pattern:

| Symptom | Root Cause | Primary Fix |
|---------|-----------|-------------|
| Generic, unhelpful answers | Missing role + context | Add explicit role, domain, and situation |
| Inconsistent output format | No format specification | Add explicit output format with example |
| Confident wrong answers (hallucination) | No uncertainty instruction | Add "if unsure, say 'I don't know'" |
| Different answers each run (high variance) | No examples anchoring behavior | Add 2-3 few-shot examples covering edge cases |
| Verbose padded responses | No length constraint | Add explicit word/sentence/bullet count limit |
| Prompt works in playground, fails in prod | Token limit exceeded or system prompt missing | Check token count; verify system prompt delivery |
| Output ignores format instructions | Instructions at wrong position | Move format instructions to END of prompt, after examples |

---

## Pre-Production Prompt Audit Checklist

Before using a prompt in production, verify all items:

```
□ Role/persona explicitly defined (who the LLM IS in this interaction)
□ Output format explicitly specified (JSON schema / markdown structure / plain prose)
□ Length constraint present for responses that should be concise
□ Hallucination guard present for factual tasks ("say I don't know if unsure")
□ Edge cases tested: empty input, ambiguous data, out-of-domain question
□ Tested on 5+ varied real inputs (not just happy path)
□ Temperature set appropriately: 0.0-0.3 for factual/structured, 0.7 for creative
□ Negative instructions paired with positive alternatives ("don't be verbose" → "respond in 3 bullets")
□ User input uses delimiters (```, <tags>, ---) to separate from instructions
□ Prompt versioned in source control with change log entry
```

**LangGraph:** Put this checklist in a PR description whenever `SystemMessage` content changes.
**Google ADK:** Run this checklist whenever `LlmAgent(instruction=...)` is modified.
