# Evaluation Metrics Reference

Python 3.14 implementations for BLEU, ROUGE, BERTScore, RAG metrics, and custom quality metrics.

## Dependencies

```bash
uv add nltk rouge-score bert-score transformers detoxify torch
```

---

## Section 1: Text Generation Metrics

```python
from __future__ import annotations

import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from bert_score import score as bert_score_fn

# Download required NLTK data on first use
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)


def calculate_bleu(reference: str, hypothesis: str) -> float:
    """Calculate sentence-level BLEU score with smoothing.

    Uses SmoothingFunction method4 (geometric mean of modified n-gram precisions
    with epsilon smoothing) to handle zero-count n-grams in short outputs.

    Args:
        reference: Ground-truth reference string.
        hypothesis: Model-generated output string.

    Returns:
        BLEU score in [0.0, 1.0].
    """
    reference_tokens = nltk.word_tokenize(reference.lower())
    hypothesis_tokens = nltk.word_tokenize(hypothesis.lower())
    smoothing = SmoothingFunction().method4
    return sentence_bleu(
        [reference_tokens],
        hypothesis_tokens,
        smoothing_function=smoothing,
    )


def calculate_rouge(reference: str, hypothesis: str) -> dict[str, float]:
    """Calculate ROUGE-1, ROUGE-2, and ROUGE-L F-measures.

    Args:
        reference: Ground-truth reference string.
        hypothesis: Model-generated output string.

    Returns:
        Dict with keys "rouge1", "rouge2", "rougeL", each containing the F-measure.
    """
    scorer = rouge_scorer.RougeScorer(
        ["rouge1", "rouge2", "rougeL"],
        use_stemmer=True,
    )
    scores = scorer.score(reference, hypothesis)
    return {
        "rouge1": scores["rouge1"].fmeasure,
        "rouge2": scores["rouge2"].fmeasure,
        "rougeL": scores["rougeL"].fmeasure,
    }


def calculate_bertscore(
    references: list[str],
    hypotheses: list[str],
    model: str = "microsoft/deberta-xlarge-mnli",
) -> dict[str, float]:
    """Calculate BERTScore precision, recall, and F1 over a batch.

    DeBERTa-xlarge-mnli is recommended for its strong NLI-tuned representations.
    For faster inference at slight quality cost, use "microsoft/deberta-base-mnli".

    Args:
        references: List of ground-truth reference strings.
        hypotheses: List of model-generated output strings (same length).
        model: HuggingFace model ID for BERTScore computation.

    Returns:
        Dict with keys "precision", "recall", "f1" — each is the mean over the batch.

    Raises:
        ValueError: If references and hypotheses have different lengths.
    """
    if len(references) != len(hypotheses):
        raise ValueError(
            f"references and hypotheses must have equal length; "
            f"got {len(references)} vs {len(hypotheses)}"
        )

    precision_tensor, recall_tensor, f1_tensor = bert_score_fn(
        hypotheses,
        references,
        model_type=model,
        verbose=False,
    )

    return {
        "precision": precision_tensor.mean().item(),
        "recall": recall_tensor.mean().item(),
        "f1": f1_tensor.mean().item(),
    }
```

---

## Section 2: RAG Evaluation Metrics

```python
import math


def calculate_mrr(
    ranked_results: list[list[str]],
    relevant_docs: list[str],
) -> float:
    """Calculate Mean Reciprocal Rank (MRR) over a set of queries.

    MRR measures how high the first relevant document appears in each ranked list.
    Best for settings where finding a single correct answer is the goal (e.g., QA).

    Args:
        ranked_results: List of ranked document-ID lists, one per query.
            ranked_results[i] is the ordered retrieval list for query i.
        relevant_docs: Flat list of all relevant document IDs across all queries.
            For per-query relevance, use calculate_ndcg instead.

    Returns:
        MRR score in [0.0, 1.0]. Returns 0.0 if no relevant doc is found.
    """
    relevant_set = set(relevant_docs)
    reciprocal_ranks: list[float] = []

    for ranked_list in ranked_results:
        rr = 0.0
        for rank, doc_id in enumerate(ranked_list, start=1):
            if doc_id in relevant_set:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

    if not reciprocal_ranks:
        return 0.0
    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def calculate_ndcg(
    ranked_results: list[str],
    relevance_scores: dict[str, int],
    k: int = 10,
) -> float:
    """Calculate Normalized Discounted Cumulative Gain (NDCG@K) for a single query.

    NDCG accounts for both the relevance grade and the rank position of each result.
    Graded relevance (0/1/2/3) is more informative than binary when available.

    Args:
        ranked_results: Ordered list of retrieved document IDs for a single query.
        relevance_scores: Mapping of document ID to graded relevance (0 = not relevant,
            higher = more relevant). Documents absent from the map are treated as 0.
        k: Cutoff rank for the evaluation.

    Returns:
        NDCG@K score in [0.0, 1.0]. Returns 0.0 if ideal DCG is 0.
    """
    def dcg(docs: list[str], scores: dict[str, int], cutoff: int) -> float:
        total = 0.0
        for i, doc_id in enumerate(docs[:cutoff], start=1):
            rel = scores.get(doc_id, 0)
            total += rel / math.log2(i + 1)
        return total

    actual_dcg = dcg(ranked_results, relevance_scores, k)
    ideal_docs = sorted(relevance_scores.keys(), key=lambda d: relevance_scores[d], reverse=True)
    ideal_dcg = dcg(ideal_docs, relevance_scores, k)

    if ideal_dcg == 0.0:
        return 0.0
    return actual_dcg / ideal_dcg


def calculate_precision_at_k(
    ranked_results: list[str],
    relevant_docs: set[str],
    k: int = 5,
) -> float:
    """Calculate Precision@K — fraction of top-K results that are relevant.

    Args:
        ranked_results: Ordered list of retrieved document IDs.
        relevant_docs: Set of relevant document IDs for this query.
        k: Cutoff rank.

    Returns:
        Precision@K in [0.0, 1.0].
    """
    if k == 0:
        return 0.0
    top_k = ranked_results[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_docs)
    return hits / k


def calculate_recall_at_k(
    ranked_results: list[str],
    relevant_docs: set[str],
    k: int = 5,
) -> float:
    """Calculate Recall@K — fraction of all relevant docs found in top-K results.

    Args:
        ranked_results: Ordered list of retrieved document IDs.
        relevant_docs: Set of all relevant document IDs for this query.
        k: Cutoff rank.

    Returns:
        Recall@K in [0.0, 1.0]. Returns 0.0 if relevant_docs is empty.
    """
    if not relevant_docs:
        return 0.0
    top_k = set(ranked_results[:k])
    hits = len(top_k & relevant_docs)
    return hits / len(relevant_docs)
```

---

## Section 3: Custom Quality Metrics

```python
from transformers import pipeline


def calculate_groundedness(
    response: str,
    context: str,
    nli_model_name: str = "microsoft/deberta-large-mnli",
) -> float:
    """Estimate response groundedness using Natural Language Inference (NLI).

    Treats the context as the NLI premise and the response as the hypothesis.
    The entailment probability indicates how well the response is supported by context.
    Low groundedness suggests hallucination or out-of-context generation.

    Args:
        response: Model-generated response to evaluate.
        context: Retrieved context that the response should be grounded in.
        nli_model_name: HuggingFace NLI model. deberta-large-mnli balances
            quality and inference speed for production use.

    Returns:
        Entailment probability in [0.0, 1.0]. Higher = better grounded.
    """
    nli_pipeline = pipeline(
        "text-classification",
        model=nli_model_name,
        top_k=None,
    )
    # NLI format: premise [SEP] hypothesis
    input_text = f"{context} [SEP] {response}"
    results: list[dict] = nli_pipeline(input_text)[0]  # type: ignore[index]

    label_map = {r["label"].upper(): r["score"] for r in results}
    # DeBERTa-MNLI labels: ENTAILMENT, NEUTRAL, CONTRADICTION
    return label_map.get("ENTAILMENT", 0.0)


def calculate_toxicity(text: str) -> float:
    """Calculate the maximum toxicity score across all toxicity dimensions.

    Uses Detoxify's 'original' Unitary model trained on the Jigsaw Toxic Comment dataset.
    Returns the worst-case score across: toxicity, severe_toxicity, obscene,
    threat, insult, identity_attack.

    Args:
        text: Text to evaluate for toxicity.

    Returns:
        Maximum toxicity score across all categories, in [0.0, 1.0].
        Higher = more toxic. Threshold for flagging: typically >= 0.5.
    """
    from detoxify import Detoxify

    results: dict[str, float] = Detoxify("original").predict(text)
    return max(results.values())
```

---

## Section 4: Metric Selection Rules

| Use Case | Primary | Why |
|----------|---------|-----|
| RAG retrieval ranking | MRR + NDCG@10 | Accounts for rank position, not just presence |
| Summarization quality | ROUGE-L + BERTScore | Content coverage + semantic similarity |
| Factual Q&A | Groundedness + BERTScore | Grounding is critical to prevent hallucination |
| Classification agent | F1-macro | Handles class imbalance; accuracy is misleading |
| Avoid BLEU for... | Long text, style-dependent outputs | N-gram overlap is too simplistic for fluency |

**Important:** Never report a single metric in isolation. Pair complementary metrics:
- ROUGE-L (lexical overlap) + BERTScore (semantic similarity) together surface cases where paraphrasing fools one but not the other.
- MRR + NDCG together surface both "did we find anything?" and "did we rank it well?".
