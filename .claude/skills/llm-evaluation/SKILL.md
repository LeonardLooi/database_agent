---
name: llm-evaluation
description: "Implement comprehensive evaluation strategies for LLM applications — automated metrics (BLEU, ROUGE, BERTScore, RAG metrics), A/B testing with statistical rigor, regression detection, and benchmarking. Use when measuring agent quality, comparing models or prompts, or building eval pipelines for LangGraph or Google ADK agents."
allowed-tools: Bash, Read, Write, Edit
metadata:
  triggers: evaluate LLM, measure quality, BLEU, ROUGE, BERTScore, MRR, NDCG, A/B test prompts, regression test, benchmark model, RAG evaluation, agent quality metrics, compare prompts, eval pipeline
  related-skills: agentic-ai-dev, google-adk, adk-eval-guide, python-testing-patterns, vector-database
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

## Iron Law

**NO EVALUATION CONCLUSION WITHOUT A BASELINE — comparing model A to model B means nothing without a defined baseline and statistical test. Every eval claim requires: metric name, sample size, statistical significance (p < 0.05), and effect size.**

# LLM Evaluation Skill — Python 3.14 + LangGraph + Google ADK

## When to Use This Skill

- Measuring quality of a RAG agent's retrieval or generation output
- Comparing two prompt variants or model versions before promoting to production
- Detecting metric regressions in CI after code or model changes
- Building an automated eval harness for a LangGraph or Google ADK agent
- Selecting the right metric family for a given eval task (retrieval vs generation vs classification)
- Establishing baseline scores before any optimization work
- Setting up inter-rater agreement to validate human evaluation labels

## Metric Selection Quick Reference

| Eval Task | Primary Metric | Secondary Metric | When NOT to Use |
|-----------|---------------|-----------------|-----------------|
| RAG Retrieval | MRR, NDCG@K | Precision@K, Recall@K | When you have no relevance judgments |
| Text Generation (summarization) | ROUGE-L, BERTScore-F1 | BLEU | When output style matters more than content |
| Classification | F1 (macro) | Precision/Recall | When class imbalance makes accuracy misleading |
| A/B Prompt Comparison | Cohen's d effect size | p-value alone | When sample size < 30 |
| RAG Generation Quality | BERTScore + Groundedness | Perplexity | For factual domain QA |

## Framework Decision Tree

```
What are you evaluating?
├── Retrieval quality (RAG) → reference/evaluation-metrics.md#rag-metrics
├── Text generation quality → reference/evaluation-metrics.md#text-generation
├── Comparing two prompts/models → reference/ab-testing.md
├── Detecting regression vs baseline → reference/ab-testing.md#regression
├── Building full eval harness → reference/evaluation-harness.md
└── Evaluating agent trajectory (tool calls, reasoning steps) → reference/trajectory-evaluation.md
```

## Reference Files

| File | Content | When to Use |
|------|---------|-------------|
| `reference/evaluation-metrics.md` | BLEU, ROUGE, BERTScore, RAG metrics (MRR, NDCG, Precision@K), classification metrics, custom groundedness | Implementing metrics for any eval task |
| `reference/ab-testing.md` | A/B test with t-test + Cohen's d, regression detector class, sample size calculator, CI/CD integration | Comparing prompts/models, detecting regressions |
| `reference/evaluation-harness.md` | Full eval harness for LangGraph agents and ADK agents, benchmark runner, inter-rater agreement | Building end-to-end eval pipeline |
| `reference/trajectory-evaluation.md` | 4-pillar evaluation (Effectiveness 40%, Efficiency 20%, Robustness 20%, Safety 20%), safety zero-tolerance, EvaluationResult structure, batch eval, pass/fail gates | Evaluating LangGraph agent trajectories end-to-end |

## Post-Code Review

After implementing any eval pipeline, dispatch the `agentic-ai-reviewer` agent to verify:
- Statistical assumptions are met (sample size, normality, independence)
- Baseline is committed and versioned (not ephemeral)
- Regression thresholds are documented and justified
- No silent metric failures (every metric error must surface, not default to 0.0)
