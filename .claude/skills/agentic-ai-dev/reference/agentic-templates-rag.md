# Agentic AI RAG Architectures

Six production-ready RAG patterns from simple to advanced, plus document ingestion pipeline.

## Pattern 1: Standard RAG

Baseline retrieval-augmented generation with embeddings, vector store, and optional reranking.

```python
from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from ...core.logging import get_logger

logger = get_logger(__name__)

RAG_PROMPT = """Answer the question based ONLY on the following context.
If the context doesn't contain enough information, say "I don't have enough information."

Context:
{context}

Question: {question}
"""


def build_standard_rag(llm, retriever, reranker=None):
    """Build a standard RAG chain.

    Args:
        llm: Chat model for generation.
        retriever: Vector store retriever.
        reranker: Optional reranker for result quality.
    """

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def retrieve_and_rerank(query: str):
        docs = retriever.invoke(query)
        if reranker:
            docs = reranker.compress_documents(docs, query)
        logger.info("rag_retrieved", doc_count=len(docs), query=query[:100])
        return docs

    prompt = ChatPromptTemplate.from_template(RAG_PROMPT)

    chain = (
        {"context": retrieve_and_rerank | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain
```

## Pattern 2: Agentic RAG

Query routing + document grading + web search fallback. The agent decides whether to search the knowledge base, web, or both.

```python
from __future__ import annotations

from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from ..state import RAGState
from ...core.logging import get_logger

logger = get_logger(__name__)


class RouteDecision(BaseModel):
    """Structured output for query routing."""
    source: Literal["vectorstore", "web_search"] = Field(
        description="Route to vectorstore for domain questions, web_search for current events"
    )


class GradeDocuments(BaseModel):
    """Grade whether a document is relevant to the query."""
    is_relevant: Literal["yes", "no"] = Field(description="Is this document relevant to the query?")


def build_agentic_rag(llm, retriever, web_search_tool, checkpointer=None):
    """Build an agentic RAG graph with query routing and document grading."""

    structured_router = llm.with_structured_output(RouteDecision)
    structured_grader = llm.with_structured_output(GradeDocuments)

    async def route_query_node(state: RAGState) -> dict:
        """Route query to vectorstore or web search."""
        query = state["messages"][-1].content
        decision = await structured_router.ainvoke([
            {"role": "system", "content": "Route this query to 'vectorstore' for domain knowledge or 'web_search' for current events."},
            {"role": "user", "content": query},
        ])
        logger.info("rag_route", source=decision.source, query=query[:100])
        return {"query": query}

    async def retrieve_node(state: RAGState) -> dict:
        """Retrieve documents from vector store."""
        docs = await retriever.ainvoke(state["query"])
        return {"documents": [{"content": d.page_content, "metadata": d.metadata} for d in docs]}

    async def grade_documents_node(state: RAGState) -> dict:
        """Grade retrieved documents for relevance."""
        relevant_docs = []
        for doc in state["documents"]:
            grade = await structured_grader.ainvoke([
                {"role": "system", "content": "Grade whether this document is relevant to the query."},
                {"role": "user", "content": f"Query: {state['query']}\nDocument: {doc['content'][:500]}"},
            ])
            if grade.is_relevant == "yes":
                relevant_docs.append(doc)

        logger.info("rag_graded", total=len(state["documents"]), relevant=len(relevant_docs))
        return {"documents": relevant_docs}

    async def web_search_node(state: RAGState) -> dict:
        """Fall back to web search when vectorstore results are insufficient."""
        results = await web_search_tool.ainvoke(state["query"])
        web_docs = [{"content": r, "metadata": {"source": "web"}} for r in results]
        return {"documents": [*state["documents"], *web_docs]}

    async def generate_node(state: RAGState) -> dict:
        """Generate answer from graded documents."""
        context = "\n\n".join(doc["content"] for doc in state["documents"])
        response = await llm.ainvoke([
            {"role": "system", "content": f"Answer based on this context:\n{context}"},
            {"role": "user", "content": state["query"]},
        ])
        return {"messages": [response], "generation": response.content}

    def decide_after_grading(state: RAGState) -> Literal["generate", "web_search"]:
        """If no relevant docs found, fall back to web search."""
        if not state["documents"]:
            return "web_search"
        return "generate"

    # --- Graph ---
    graph = StateGraph(RAGState)
    graph.add_node("route", route_query_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("grade", grade_documents_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("route")
    graph.add_edge("route", "retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_conditional_edges("grade", decide_after_grading)
    graph.add_edge("web_search", "generate")
    graph.add_edge("generate", END)

    return graph.compile(checkpointer=checkpointer)
```

## Pattern 3: Self-RAG

Generation grading + hallucination check loop. The agent evaluates its own output.

```python
class HallucinationGrade(BaseModel):
    """Check if generation is grounded in documents."""
    is_grounded: Literal["yes", "no"] = Field(description="Is the answer supported by the documents?")


class AnswerGrade(BaseModel):
    """Check if generation actually answers the question."""
    is_useful: Literal["yes", "no"] = Field(description="Does this answer address the question?")


def build_self_rag(llm, retriever, checkpointer=None):
    """Self-RAG: generate, check hallucination, check usefulness, retry if needed."""

    grounded_checker = llm.with_structured_output(HallucinationGrade)
    answer_checker = llm.with_structured_output(AnswerGrade)

    async def check_hallucination_node(state: RAGState) -> dict:
        context = "\n".join(doc["content"] for doc in state["documents"])
        grade = await grounded_checker.ainvoke([
            {"role": "system", "content": "Is this answer grounded in the documents?"},
            {"role": "user", "content": f"Documents:\n{context}\n\nAnswer:\n{state['generation']}"},
        ])
        return {"is_grounded": grade.is_grounded == "yes"}

    async def check_answer_node(state: RAGState) -> dict:
        grade = await answer_checker.ainvoke([
            {"role": "system", "content": "Does this answer address the original question?"},
            {"role": "user", "content": f"Question: {state['query']}\nAnswer: {state['generation']}"},
        ])
        if grade.is_useful == "no":
            return {"messages": [AIMessage(content="Let me search for more information...")]}
        return {}

    def hallucination_router(state: RAGState) -> str:
        if not state["is_grounded"]:
            logger.warning("hallucination_detected", query=state["query"][:100])
            return "retrieve"  # Re-retrieve and regenerate
        return "check_answer"

    # Compose into graph with: retrieve → grade → generate → check_hallucination → check_answer → END
```

## Pattern 4: Graph RAG

Entity-relationship queries using a graph database (Neo4j).

```python
async def graph_rag_retrieve(query: str, graph_db, llm) -> list[dict]:
    """Use LLM to generate Cypher query, then retrieve from Neo4j."""
    cypher_prompt = f"""Generate a Cypher query for Neo4j to answer: {query}
    Schema: (Person)-[:WORKS_AT]->(Company), (Person)-[:KNOWS]->(Person)
    Return ONLY the Cypher query."""

    cypher = await llm.ainvoke([{"role": "user", "content": cypher_prompt}])
    results = graph_db.query(cypher.content)
    return [{"content": str(r), "metadata": {"source": "graph_db"}} for r in results]
```

## Pattern 5: HyDE RAG

Hypothetical Document Embeddings — generate a hypothetical answer, embed it, use for retrieval.

```python
async def hyde_retrieve(query: str, llm, embeddings, vector_store) -> list:
    """HyDE: Generate hypothetical document, use its embedding for retrieval."""
    # Step 1: Generate hypothetical answer
    hypothetical = await llm.ainvoke([
        {"role": "system", "content": "Write a detailed paragraph that would answer this question."},
        {"role": "user", "content": query},
    ])

    # Step 2: Embed the hypothetical document
    hyde_embedding = await embeddings.aembed_query(hypothetical.content)

    # Step 3: Search vector store with hypothetical embedding
    docs = vector_store.similarity_search_by_vector(hyde_embedding, k=5)
    logger.info("hyde_retrieved", doc_count=len(docs))
    return docs
```

## Pattern 6: Multi-Step RAG

Query decomposition + parallel retrieval for complex questions.

```python
class QueryDecomposition(BaseModel):
    """Decompose a complex query into sub-queries."""
    sub_queries: list[str] = Field(description="List of simpler sub-queries")


async def multi_step_retrieve(query: str, llm, retriever) -> list:
    """Decompose query → parallel retrieval → merge results."""
    import asyncio

    # Step 1: Decompose
    decomposer = llm.with_structured_output(QueryDecomposition)
    decomposition = await decomposer.ainvoke([
        {"role": "system", "content": "Break this complex question into 2-4 simpler sub-questions."},
        {"role": "user", "content": query},
    ])

    # Step 2: Parallel retrieval
    tasks = [retriever.ainvoke(sq) for sq in decomposition.sub_queries]
    all_results = await asyncio.gather(*tasks)

    # Step 3: Deduplicate and merge
    seen_ids = set()
    merged = []
    for docs in all_results:
        for doc in docs:
            doc_id = doc.metadata.get("id", doc.page_content[:100])
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                merged.append(doc)

    logger.info("multi_step_retrieved", sub_queries=len(decomposition.sub_queries), total_docs=len(merged))
    return merged
```

## Document Ingestion Pipeline

**File:** `src/<service>/rag/indexing/pipeline.py`

```python
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredHTMLLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter


def build_ingestion_pipeline(embeddings, vector_store):
    """Build a document ingestion pipeline: load → split → embed → index."""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    loaders = {
        ".pdf": PyPDFLoader,
        ".txt": TextLoader,
        ".html": UnstructuredHTMLLoader,
    }

    async def ingest(file_path: str, metadata: dict | None = None) -> int:
        """Ingest a document into the vector store.

        Returns:
            Number of chunks indexed.
        """
        ext = "." + file_path.rsplit(".", 1)[-1].lower()
        loader_cls = loaders.get(ext)
        if not loader_cls:
            raise ValueError(f"Unsupported file type: {ext}")

        docs = loader_cls(file_path).load()

        # Add metadata
        if metadata:
            for doc in docs:
                doc.metadata.update(metadata)

        chunks = splitter.split_documents(docs)
        await vector_store.aadd_documents(chunks)

        logger.info("ingestion_complete", file=file_path, chunks=len(chunks))
        return len(chunks)

    return ingest
```

## RAG Selection Guide

| Pattern | Use When | Complexity | Quality |
|---------|----------|------------|---------|
| Standard RAG | Simple Q&A over documents | Low | Good |
| Agentic RAG | Need routing + fallback | Medium | Better |
| Self-RAG | Hallucination is unacceptable | Medium | Best |
| Graph RAG | Entity-relationship queries | High | Best for structured data |
| HyDE RAG | Short/ambiguous queries | Medium | Better retrieval |
| Multi-Step RAG | Complex multi-part questions | Medium | Best for complex queries |
