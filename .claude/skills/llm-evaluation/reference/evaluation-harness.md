# Evaluation Harness Reference

End-to-end eval harness for LangGraph and Google ADK agents — benchmark runner,
inter-rater agreement, LLM judge, and full pytest example.

## Dependencies

```bash
uv add scipy numpy pydantic langchain-core langgraph google-adk
uv add --dev pytest pytest-asyncio
```

---

## Section 1: BenchmarkRunner Class

```python
from __future__ import annotations

import asyncio
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types


@dataclass
class EvalCase:
    """A single evaluation test case.

    Attributes:
        input: The user query or prompt sent to the agent.
        expected: Ground-truth reference output for metric computation.
        context: Optional retrieved context (for groundedness evaluation).
        metadata: Arbitrary key-value pairs for filtering or grouping results.
    """

    input: str
    expected: str
    context: str | None = None
    metadata: dict = field(default_factory=dict)


class BenchmarkRunner:
    """Run a suite of EvalCases against a LangGraph or ADK agent and aggregate scores.

    Supports pluggable metric functions and produces mean, std, min, max, p50, p95
    for each metric across the full test suite.

    Usage (LangGraph):
        runner = BenchmarkRunner(test_cases=cases, metrics=[calculate_bleu])
        report = await runner.run_langgraph(agent_fn=my_agent)

    Usage (ADK):
        runner = BenchmarkRunner(test_cases=cases, metrics=[calculate_bleu])
        report = await runner.run_adk(runner=InMemoryRunner(agent=my_adk_agent))
    """

    def __init__(
        self,
        test_cases: list[EvalCase],
        metrics: list[Callable[..., float]],
    ) -> None:
        """Initialize with test cases and metric callables.

        Args:
            test_cases: List of EvalCase instances to evaluate.
            metrics: List of callables with signature
                ``(reference: str, hypothesis: str) -> float``.
                For batch metrics (e.g. BERTScore), wrap them to accept
                single strings and compute individually.
        """
        if not test_cases:
            raise ValueError("test_cases must not be empty")
        if not metrics:
            raise ValueError("metrics must not be empty")

        self.test_cases = test_cases
        self.metrics = metrics

    async def run_langgraph(
        self,
        agent_fn: Callable[[dict[str, Any]], Any],
        output_key: str = "output",
    ) -> dict[str, list[float]]:
        """Run all test cases through a LangGraph agent and collect raw scores.

        Args:
            agent_fn: Async callable accepting ``{"input": str}`` and returning
                a dict containing at least ``output_key``.
            output_key: Key in the agent response dict holding the text output.

        Returns:
            Dict mapping metric function name to list of per-case scores.
        """
        scores: dict[str, list[float]] = {m.__name__: [] for m in self.metrics}

        for case in self.test_cases:
            result = await agent_fn({"input": case.input})
            hypothesis: str = result[output_key]

            for metric_fn in self.metrics:
                score = metric_fn(case.expected, hypothesis)
                scores[metric_fn.__name__].append(score)

        return scores

    async def run_adk(
        self,
        runner: InMemoryRunner,
        user_id: str = "benchmark-user",
    ) -> dict[str, list[float]]:
        """Run all test cases through a Google ADK agent and collect raw scores.

        Args:
            runner: Configured InMemoryRunner wrapping the ADK agent under test.
            user_id: ADK user ID for all eval sessions.

        Returns:
            Dict mapping metric function name to list of per-case scores.
        """
        scores: dict[str, list[float]] = {m.__name__: [] for m in self.metrics}

        for i, case in enumerate(self.test_cases):
            session_id = f"benchmark-{i}"
            user_message = genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=case.input)],
            )

            hypothesis = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_message,
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    hypothesis = event.content.parts[0].text or ""

            for metric_fn in self.metrics:
                score = metric_fn(case.expected, hypothesis)
                scores[metric_fn.__name__].append(score)

        return scores

    def aggregate(self, scores: dict[str, list[float]]) -> dict[str, dict[str, float]]:
        """Compute aggregate statistics over per-case metric scores.

        Args:
            scores: Output from run_langgraph() or run_adk().

        Returns:
            Dict mapping metric name to stats: mean, std, min, max, p50, p95.
        """
        result: dict[str, dict[str, float]] = {}

        for metric_name, values in scores.items():
            if not values:
                continue
            arr = sorted(values)
            n = len(arr)
            result[metric_name] = {
                "mean": statistics.mean(arr),
                "std": statistics.stdev(arr) if n > 1 else 0.0,
                "min": arr[0],
                "max": arr[-1],
                "p50": arr[n // 2],
                "p95": arr[min(int(n * 0.95), n - 1)],
                "n": float(n),
            }

        return result
```

---

## Section 2: Inter-Rater Agreement

```python
from sklearn.metrics import cohen_kappa_score


def calculate_cohen_kappa(
    rater1: list[int],
    rater2: list[int],
) -> dict[str, float | str]:
    """Calculate Cohen's Kappa inter-rater agreement between two human annotators.

    Use before automating evaluations with LLM judges — low kappa (< 0.6) means
    even human raters disagree, making automated metrics unreliable for that task.

    Args:
        rater1: List of integer label assignments from rater 1.
        rater2: List of integer label assignments from rater 2 (same length).

    Returns:
        Dict with:
            - kappa: Cohen's kappa in [-1.0, 1.0]
            - interpretation: human-readable agreement level

    Raises:
        ValueError: If rater1 and rater2 have different lengths.
    """
    if len(rater1) != len(rater2):
        raise ValueError(
            f"rater1 and rater2 must have equal length; "
            f"got {len(rater1)} vs {len(rater2)}"
        )

    kappa = float(cohen_kappa_score(rater1, rater2))

    if kappa < 0.0:
        interpretation = "Poor (worse than chance)"
    elif kappa < 0.2:
        interpretation = "Slight"
    elif kappa < 0.4:
        interpretation = "Fair"
    elif kappa < 0.6:
        interpretation = "Moderate"
    elif kappa < 0.8:
        interpretation = "Substantial"
    else:
        interpretation = "Almost Perfect"

    return {"kappa": kappa, "interpretation": interpretation}
```

---

## Section 3: LLM Judge Integration (Basic)

For production use with position bias mitigation and rubric generation, read
`agentic-ai-dev/reference/llm-judge-advanced.md` first.

```python
from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate


class CriterionScore(BaseModel):
    """Score for a single evaluation criterion."""

    score: int = Field(ge=1, le=5, description="Score from 1 (poor) to 5 (excellent)")
    evidence: str = Field(description="Quoted span from the response supporting this score")
    justification: str = Field(description="One-sentence reasoning for the score")


class JudgeOutput(BaseModel):
    """Structured output from the LLM judge."""

    scores: dict[str, CriterionScore]


_JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an impartial evaluator. Score the RESPONSE to the QUESTION "
        "on the provided criteria. Be strict and evidence-based.",
    ),
    (
        "human",
        "QUESTION: {question}\n\nRESPONSE: {response}\n\nCRITERIA: {criteria}\n\n"
        "Return a JSON object with a 'scores' key mapping each criterion to "
        "{{score, evidence, justification}}.",
    ),
])


async def llm_judge(
    response: str,
    question: str,
    criteria: list[str],
    llm: BaseChatModel,
) -> dict[str, dict]:
    """Score a response against explicit criteria using an LLM judge.

    Returns structured scores rather than free-form text to enable
    automated metric tracking. Uses Pydantic-validated output to prevent
    hallucinated schema.

    Args:
        response: The agent output to evaluate.
        question: The original user question the response addresses.
        criteria: List of evaluation dimensions (e.g., ["accuracy", "conciseness"]).
        llm: Any LangChain-compatible chat model (Gemini, Claude, GPT-4o, etc.).

    Returns:
        Dict mapping criterion name to {"score": int, "evidence": str, "justification": str}.

    Note:
        For production: read agentic-ai-dev/reference/llm-judge-advanced.md for
        position bias mitigation, calibration, and rubric generation patterns.
    """
    structured_llm = llm.with_structured_output(JudgeOutput)
    chain = _JUDGE_PROMPT | structured_llm

    result: JudgeOutput = await chain.ainvoke({
        "question": question,
        "response": response,
        "criteria": ", ".join(criteria),
    })

    return {
        criterion: {
            "score": score.score,
            "evidence": score.evidence,
            "justification": score.justification,
        }
        for criterion, score in result.scores.items()
    }
```

---

## Section 4: Complete Pytest Example — LangGraph RAG Agent

Full eval pipeline integrating BenchmarkRunner, RegressionDetector, and assertion gates.

```python
# tests/eval/test_rag_full_pipeline.py
from __future__ import annotations

import pytest
from collections.abc import Callable

from eval.ab_testing import RegressionDetector
from eval.evaluation_harness import BenchmarkRunner, EvalCase
from eval.evaluation_metrics import (
    calculate_bleu,
    calculate_bertscore,
    calculate_mrr,
    calculate_groundedness,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def eval_cases() -> list[EvalCase]:
    """Minimum viable eval set — extend to >=30 cases for production baselines."""
    return [
        EvalCase(
            input="What is the capital of France?",
            expected="The capital of France is Paris.",
            context="France is a country in Western Europe. Its capital city is Paris.",
        ),
        EvalCase(
            input="Explain transformer attention in one sentence.",
            expected=(
                "Transformer attention computes a weighted sum of value vectors "
                "where weights are determined by query-key dot products."
            ),
            context=(
                "The attention mechanism assigns different weights to different "
                "positions in the input sequence based on their relevance."
            ),
        ),
    ]


@pytest.fixture
def baseline_metrics() -> dict[str, float]:
    """Committed baseline — update after deliberate model promotion."""
    return {
        "calculate_bleu": 0.65,
        "bertscore_f1": 0.84,
        "mrr": 0.78,
        "groundedness": 0.72,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _invoke_rag_agent(
    agent_fn: Callable,
    cases: list[EvalCase],
) -> tuple[list[float], list[float], list[list[str]]]:
    """Run agent over cases; return BLEU scores, BERTScore inputs, MRR ranked lists."""
    bleu_scores: list[float] = []
    refs: list[str] = []
    hyps: list[str] = []
    ranked_lists: list[list[str]] = []
    all_relevant: list[str] = []
    groundedness_scores: list[float] = []

    for case in cases:
        result = await agent_fn({"input": case.input})
        output: str = result["output"]
        retrieved: list[str] = result.get("retrieved_doc_ids", [])

        bleu_scores.append(calculate_bleu(case.expected, output))
        refs.append(case.expected)
        hyps.append(output)
        ranked_lists.append(retrieved)

        if case.context:
            groundedness_scores.append(
                calculate_groundedness(output, case.context)
            )

    bs_result = calculate_bertscore(refs, hyps)
    mrr = calculate_mrr(ranked_lists, all_relevant)

    return {
        "calculate_bleu": sum(bleu_scores) / len(bleu_scores),
        "bertscore_f1": bs_result["f1"],
        "mrr": mrr,
        "groundedness": (
            sum(groundedness_scores) / len(groundedness_scores)
            if groundedness_scores
            else 0.0
        ),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_benchmark_aggregate(
    rag_agent_fn,          # fixture: async callable -> {"output": str, "retrieved_doc_ids": list[str]}
    eval_cases: list[EvalCase],
) -> None:
    """Verify BenchmarkRunner produces aggregate stats for all metrics."""
    runner = BenchmarkRunner(
        test_cases=eval_cases,
        metrics=[calculate_bleu],
    )
    raw_scores = await runner.run_langgraph(agent_fn=rag_agent_fn)
    aggregated = runner.aggregate(raw_scores)

    assert "calculate_bleu" in aggregated
    stats = aggregated["calculate_bleu"]
    assert all(k in stats for k in ["mean", "std", "min", "max", "p50", "p95"])
    assert 0.0 <= stats["mean"] <= 1.0


@pytest.mark.asyncio
async def test_no_regression_against_baseline(
    rag_agent_fn,
    eval_cases: list[EvalCase],
    baseline_metrics: dict[str, float],
) -> None:
    """Assert no metric drops more than 5% relative to the committed baseline."""
    detector = RegressionDetector(baseline_metrics, threshold=0.05)
    current_metrics = await _invoke_rag_agent(rag_agent_fn, eval_cases)
    report = detector.check_for_regression(current_metrics)

    assert not report["has_regression"], (
        f"Metric regression detected — failing CI.\n"
        f"Regressions: {report['regressions']}\n"
        f"Current: {current_metrics}\n"
        f"Baseline: {baseline_metrics}"
    )


@pytest.mark.asyncio
async def test_groundedness_above_threshold(
    rag_agent_fn,
    eval_cases: list[EvalCase],
) -> None:
    """Assert mean groundedness stays above 0.70 (NLI entailment score)."""
    scores: list[float] = []
    for case in eval_cases:
        if case.context is None:
            continue
        result = await rag_agent_fn({"input": case.input})
        score = calculate_groundedness(result["output"], case.context)
        scores.append(score)

    if scores:
        mean_groundedness = sum(scores) / len(scores)
        assert mean_groundedness >= 0.70, (
            f"Mean groundedness {mean_groundedness:.3f} < 0.70 threshold. "
            "Agent may be hallucinating outside provided context."
        )
```
