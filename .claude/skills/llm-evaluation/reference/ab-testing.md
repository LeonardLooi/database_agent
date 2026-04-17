# A/B Testing and Regression Detection Reference

Statistical rigor for prompt/model comparison and CI regression detection.

## Dependencies

```bash
uv add scipy numpy
uv add --dev pytest pytest-asyncio
```

---

## Section 1: ABTest Class

```python
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
from scipy import stats


@dataclass
class ABTest:
    """Statistically rigorous A/B comparison between two prompt or model variants.

    Collects per-variant scores then runs an independent-samples t-test with
    Cohen's d effect size. Requires at least 30 samples per variant for the
    central limit theorem to provide t-test validity.

    Usage:
        test = ABTest()
        for score in variant_a_scores:
            test.add_result("control", score)
        for score in variant_b_scores:
            test.add_result("treatment", score)
        report = test.analyze()
    """

    _results: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list),
        init=False,
        repr=False,
    )

    def add_result(self, variant: str, score: float) -> None:
        """Record a single evaluation score for a variant.

        Args:
            variant: Variant name — typically "control" and "treatment".
            score: Numeric evaluation score (e.g., BERTScore F1, BLEU, MRR).
        """
        self._results[variant].append(score)

    def analyze(self, alpha: float = 0.05) -> dict:
        """Run two-sided independent t-test and compute Cohen's d effect size.

        Args:
            alpha: Significance threshold. Use 0.05 for exploration, 0.01 for
                production promotion decisions.

        Returns:
            Dict containing:
                - variants: per-variant mean, std, n
                - t_stat: t-statistic
                - p_value: two-sided p-value
                - cohens_d: standardized effect size
                - effect_size_interpretation: "negligible" | "small" | "medium" | "large"
                - significant: bool (p < alpha)
                - winner: variant name with higher mean, or None if not significant
                - warnings: list of data quality warnings

        Raises:
            ValueError: If fewer than 2 variants or any variant has no results.
        """
        variants = list(self._results.keys())
        if len(variants) < 2:
            raise ValueError(
                f"ABTest requires at least 2 variants; got {variants}"
            )

        warnings: list[str] = []
        summary: dict[str, dict] = {}
        for name, scores in self._results.items():
            arr = np.array(scores, dtype=float)
            mean_val = float(arr.mean())
            std_val = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
            summary[name] = {"mean": mean_val, "std": std_val, "n": len(scores)}

            if len(scores) < 30:
                warnings.append(
                    f"Variant '{name}' has only {len(scores)} samples — "
                    "t-test validity requires n >= 30."
                )
            cv = std_val / mean_val if mean_val != 0 else 0.0
            if cv > 0.3:
                warnings.append(
                    f"Variant '{name}' has high variance (CV={cv:.2f}) — "
                    "consider collecting more samples or checking for outliers."
                )

        # Use first two variants for the primary comparison
        a_name, b_name = variants[0], variants[1]
        a_scores = np.array(self._results[a_name], dtype=float)
        b_scores = np.array(self._results[b_name], dtype=float)

        t_stat, p_value = stats.ttest_ind(a_scores, b_scores, equal_var=False)

        # Pooled standard deviation for Cohen's d
        pooled_std = math.sqrt(
            (a_scores.std(ddof=1) ** 2 + b_scores.std(ddof=1) ** 2) / 2
        )
        cohens_d = (
            float((a_scores.mean() - b_scores.mean()) / pooled_std)
            if pooled_std > 0
            else 0.0
        )

        significant = float(p_value) < alpha
        winner: str | None = None
        if significant:
            winner = a_name if summary[a_name]["mean"] > summary[b_name]["mean"] else b_name

        return {
            "variants": summary,
            "t_stat": float(t_stat),
            "p_value": float(p_value),
            "cohens_d": cohens_d,
            "effect_size_interpretation": self.interpret_cohens_d(cohens_d),
            "significant": significant,
            "winner": winner,
            "warnings": warnings,
        }

    @staticmethod
    def interpret_cohens_d(d: float) -> str:
        """Interpret Cohen's d effect size magnitude.

        Args:
            d: Cohen's d value (can be negative; absolute value is used).

        Returns:
            Human-readable label: "negligible", "small", "medium", or "large".
        """
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible"
        if abs_d < 0.5:
            return "small"
        if abs_d < 0.8:
            return "medium"
        return "large"

    @staticmethod
    def minimum_sample_size(
        effect_size: float = 0.5,
        alpha: float = 0.05,
        power: float = 0.8,
    ) -> int:
        """Calculate minimum per-variant sample size for given statistical power.

        Uses a two-sided t-test approximation via the normal distribution.
        Conservative: add ~10% buffer in practice.

        Args:
            effect_size: Expected Cohen's d (0.2=small, 0.5=medium, 0.8=large).
                Default 0.5 (medium) is a reasonable prior for prompt changes.
            alpha: Type I error rate (significance threshold).
            power: Desired statistical power (1 - Type II error rate).

        Returns:
            Minimum number of observations required per variant.
        """
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_beta = stats.norm.ppf(power)
        n = ((z_alpha + z_beta) / effect_size) ** 2
        return math.ceil(n)
```

---

## Section 2: RegressionDetector Class

```python
class RegressionDetector:
    """Detect metric regressions relative to a committed baseline.

    Compares new evaluation results against stored baseline values. Flags any
    metric that drops beyond the configured relative threshold.

    Usage in CI:
        detector = RegressionDetector(baseline_results={"bleu": 0.72, "mrr": 0.81})
        report = detector.check_for_regression(new_results)
        assert not report["has_regression"], report["regressions"]
    """

    def __init__(
        self,
        baseline_results: dict[str, float],
        threshold: float = 0.05,
    ) -> None:
        """Initialize with baseline metric scores.

        Args:
            baseline_results: Dict mapping metric name to baseline value.
            threshold: Relative drop that constitutes a regression.
                Default 0.05 = 5% relative decrease triggers a failure.
        """
        self.baseline_results = dict(baseline_results)
        self.threshold = threshold

    def check_for_regression(self, new_results: dict[str, float]) -> dict:
        """Compare new scores against baseline and flag regressions.

        Args:
            new_results: Dict mapping metric name to current score.

        Returns:
            Dict containing:
                - has_regression: bool
                - regressions: list of dicts with metric, baseline, current, relative_change
                - improvements: list of dicts with metric, baseline, current, relative_change
                - unchanged: list of metric names within threshold
        """
        regressions: list[dict] = []
        improvements: list[dict] = []
        unchanged: list[str] = []

        for metric, baseline_val in self.baseline_results.items():
            if metric not in new_results:
                regressions.append({
                    "metric": metric,
                    "baseline": baseline_val,
                    "current": None,
                    "relative_change": None,
                    "reason": "metric missing from new results",
                })
                continue

            current_val = new_results[metric]
            if baseline_val == 0.0:
                relative_change = 0.0 if current_val == 0.0 else float("inf")
            else:
                relative_change = (current_val - baseline_val) / abs(baseline_val)

            entry = {
                "metric": metric,
                "baseline": baseline_val,
                "current": current_val,
                "relative_change": relative_change,
            }

            if relative_change < -self.threshold:
                regressions.append(entry)
            elif relative_change > self.threshold:
                improvements.append(entry)
            else:
                unchanged.append(metric)

        return {
            "has_regression": len(regressions) > 0,
            "regressions": regressions,
            "improvements": improvements,
            "unchanged": unchanged,
        }

    def update_baseline(self, new_results: dict[str, float]) -> None:
        """Promote new results to become the baseline.

        Call this after a deliberate model/prompt promotion to prevent future
        comparisons against an outdated baseline.

        Args:
            new_results: New baseline metric values.
        """
        self.baseline_results.update(new_results)
```

---

## Section 3: LangGraph Eval Integration

Wire `RegressionDetector` into a pytest suite that evaluates a LangGraph RAG agent.

```python
# tests/eval/test_rag_regression.py
from __future__ import annotations

import pytest
from collections.abc import Callable

from eval.metrics import calculate_bertscore, calculate_bleu, calculate_mrr
from eval.ab_testing import RegressionDetector


async def run_eval(
    agent_fn: Callable,
    test_cases: list[dict],
) -> dict[str, float]:
    """Run a LangGraph agent over test cases and return aggregate metrics.

    Args:
        agent_fn: Async callable that accepts {"input": str} and returns
            {"output": str, "retrieved_docs": list[str]}.
        test_cases: List of dicts with keys: input, expected, relevant_docs.

    Returns:
        Dict of metric name to mean score across all test cases.
    """
    bleu_scores: list[float] = []
    bertscore_refs: list[str] = []
    bertscore_hyps: list[str] = []
    ranked_lists: list[list[str]] = []
    all_relevant: list[str] = []

    for case in test_cases:
        result = await agent_fn({"input": case["input"]})
        output: str = result["output"]
        retrieved: list[str] = result.get("retrieved_docs", [])

        bleu_scores.append(calculate_bleu(case["expected"], output))
        bertscore_refs.append(case["expected"])
        bertscore_hyps.append(output)
        ranked_lists.append(retrieved)
        all_relevant.extend(case.get("relevant_docs", []))

    bs = calculate_bertscore(bertscore_refs, bertscore_hyps)
    mrr = calculate_mrr(ranked_lists, all_relevant)

    return {
        "bleu": sum(bleu_scores) / len(bleu_scores),
        "bertscore_f1": bs["f1"],
        "mrr": mrr,
    }


@pytest.fixture
def baseline_metrics() -> dict[str, float]:
    """Committed baseline scores — update via RegressionDetector.update_baseline()
    after a deliberate promotion."""
    return {"bleu": 0.72, "bertscore_f1": 0.88, "mrr": 0.81}


@pytest.mark.asyncio
async def test_no_regression(
    rag_agent,           # fixture: async callable wrapping your LangGraph agent
    test_cases,          # fixture: list[dict] with input/expected/relevant_docs
    baseline_metrics: dict[str, float],
) -> None:
    """Assert no metric regresses more than 5% relative to baseline."""
    detector = RegressionDetector(baseline_metrics, threshold=0.05)
    results = await run_eval(rag_agent, test_cases)
    report = detector.check_for_regression(results)
    assert not report["has_regression"], (
        f"Regression detected: {report['regressions']}"
    )
```

---

## Section 4: ADK Eval Integration

Same regression pattern using `InMemoryRunner` for Google ADK agents.

```python
# tests/eval/test_adk_regression.py
from __future__ import annotations

import pytest
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from eval.metrics import calculate_bertscore, calculate_bleu
from eval.ab_testing import RegressionDetector


async def run_adk_eval(
    runner: InMemoryRunner,
    test_cases: list[dict],
    user_id: str = "eval-user",
    session_id: str = "eval-session",
) -> dict[str, float]:
    """Run ADK agent over test cases and return aggregate metrics.

    Args:
        runner: Configured InMemoryRunner wrapping the ADK agent under test.
        test_cases: List of dicts with keys: input, expected.
        user_id: ADK user identifier for the eval session.
        session_id: ADK session identifier for the eval session.

    Returns:
        Dict of metric name to mean score across all test cases.
    """
    bleu_scores: list[float] = []
    refs: list[str] = []
    hyps: list[str] = []

    for case in test_cases:
        user_message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=case["input"])],
        )
        final_response = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=f"{session_id}-{case['input'][:16]}",
            new_message=user_message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text or ""

        bleu_scores.append(calculate_bleu(case["expected"], final_response))
        refs.append(case["expected"])
        hyps.append(final_response)

    bs = calculate_bertscore(refs, hyps)
    return {
        "bleu": sum(bleu_scores) / len(bleu_scores),
        "bertscore_f1": bs["f1"],
    }


@pytest.fixture
def baseline_metrics() -> dict[str, float]:
    return {"bleu": 0.70, "bertscore_f1": 0.86}


@pytest.mark.asyncio
async def test_adk_no_regression(
    my_adk_agent,        # fixture: your ADK Agent instance
    adk_test_cases,      # fixture: list[dict] with input/expected
    baseline_metrics: dict[str, float],
) -> None:
    """Assert ADK agent does not regress more than 5% on any metric."""
    runner = InMemoryRunner(agent=my_adk_agent)
    detector = RegressionDetector(baseline_metrics, threshold=0.05)
    results = await run_adk_eval(runner, adk_test_cases)
    report = detector.check_for_regression(results)
    assert not report["has_regression"], (
        f"ADK regression detected: {report['regressions']}"
    )
```

---

## Section 5: Statistical Rules

| Rule | Value | Rationale |
|------|-------|-----------|
| Minimum sample size | 30 per variant | Central limit theorem validity for t-test |
| Significance threshold (exploration) | p < 0.05 | Standard convention |
| Significance threshold (production) | p < 0.01 | Stricter bar for irreversible model promotion |
| Effect size — promote | Cohen's d >= 0.5 (medium+) | Small effects may not justify deployment cost |
| Effect size — reject | Cohen's d < 0.2 (negligible) | Even if significant, effect is practically meaningless |
| High variance warning | CV (std/mean) > 0.3 | Investigate outliers before drawing conclusions |
| Regression threshold | 5% relative drop | Default; tighten to 2% for critical accuracy metrics |

**Never promote based on p-value alone.** A tiny p-value with negligible Cohen's d means the sample is large enough to detect noise, not a meaningful improvement. Always report both.
