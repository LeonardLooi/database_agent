---
description: Scaffold a full RAG pipeline — chunking → embedding → storage (pgvector or Weaviate) → retrieval → reranking → LangChain or custom Python. Generates production-ready pipeline with pinned model, batch embedding, null guards, error handling, and optional reranker.
argument-hint: "[pipeline name] [storage: pgvector|weaviate|both] [use case description]"
allowed-tools: Bash, Read, Write, Edit
disable-model-invocation: true
---

# Scaffold RAG Pipeline

Generate a complete retrieval-augmented generation pipeline.

**Input:** $ARGUMENTS

## Steps

1. **Load the `vector-database` skill** — read `SKILL.md` and `references/rag-pipeline-patterns.md` for templates and anti-patterns.

2. **Gather requirements** — Extract from `$ARGUMENTS` or ask:
   - Pipeline name (snake_case, e.g., `vendor_rag`)
   - Vector store: `pgvector`, `weaviate`, or `both` (two-stage)
   - Embedding model (from skill model table)
   - Chunking strategy (recursive / sentence / paragraph / fixed) + chunk size
   - Reranking: Cohere / cross-encoder / none (must justify "none" for production)
   - Framework: LangChain integration or custom Python
   - Use case (determines retrieval filters and query patterns)

3. **Generate pipeline files**:

   ### `embedding_service.py`
   - `EMBEDDING_MODEL` constant (not per-call string)
   - `EmbeddingService` class with `embed(text)` and `embed_batch(texts)` async methods
   - Rate-limit and timeout error handling (retry 3× with exponential backoff)
   - `try/except` on all API calls — no silent failures

   ### `chunking.py`
   - Chunking function with strategy from requirements
   - `RecursiveCharacterTextSplitter` with non-zero overlap
   - Returns `List[{"text": str, "metadata": dict}]`

   ### `{storage}_retriever.py` (pgvector and/or weaviate)
   - Async retrieval function with null guard
   - Structured filter support (city, category, etc.)
   - `top_k` parameter → retrieves 3× final count for reranking room

   ### `reranker.py` (if not "none")
   - Cohere rerank wrapper or cross-encoder
   - Accepts merged candidates from both retrieval stages if two-stage

   ### `pipeline.py`
   - Orchestrates: query → embed query → retrieve → rerank → format context
   - Score threshold filter (configurable, default 0.5)
   - Logging of retrieval counts and latency
   - Returns `{"results": [...], "context": str, "metadata": {...}}`

   ### `tests/test_{pipeline_name}.py`
   - Unit test: embedding service returns correct shape
   - Unit test: chunking respects chunk_size and overlap
   - Integration test: retrieve → rerank returns expected structure

4. **Run `rag-pipeline-reviewer` agent** on all generated files.

5. **Save files** to `src/{pipeline_name}/` or infer from project structure.

6. **Report** generated files, reviewer findings, and how to run the pipeline.

$ARGUMENTS
