# Agentic AI Testing Patterns

Comprehensive testing patterns for LangGraph agents, RAG systems, and FastAPI endpoints.

## pytest Configuration

**File:** `pyproject.toml` (testing section)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks integration tests requiring external services",
]
```

**File:** `tests/conftest.py`

```python
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from my_agent_service.core.config import Settings
from my_agent_service.llm.providers import LLMProviderFactory


@pytest.fixture
def settings():
    """Test settings with safe defaults."""
    return Settings(
        anthropic_api_key="sk-ant-test-key",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        checkpoint_db_uri="postgresql://test:test@localhost:5432/test",
        app_env="development",
    )


@pytest.fixture
def mock_llm():
    """Mock LLM that returns predictable responses."""
    llm = AsyncMock()
    llm.ainvoke.return_value = AIMessage(content="Test response")
    llm.bind_tools.return_value = llm
    llm.with_structured_output.return_value = llm
    llm.with_fallbacks.return_value = llm
    return llm


@pytest.fixture
def mock_provider_factory(mock_llm):
    """Mock LLM provider factory."""
    factory = AsyncMock(spec=LLMProviderFactory)
    factory.get_default.return_value = mock_llm
    factory.get.return_value = mock_llm
    factory.get_model.return_value = mock_llm
    factory.get_fallback_chain.return_value = mock_llm
    return factory


@pytest.fixture
def memory_checkpointer():
    """In-memory checkpointer for tests — never use in production."""
    return MemorySaver()


@pytest.fixture
def thread_id():
    """Consistent thread ID for test conversations."""
    return "test-thread-001"
```

## Basic Agent Tests

**File:** `tests/test_agent_basic.py`

```python
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from my_agent_service.agents.graphs.react_agent import build_react_agent


class TestReActAgent:
    """Basic agent functionality tests."""

    async def test_agent_responds_to_simple_message(self, mock_provider_factory, memory_checkpointer, thread_id):
        """Agent should produce a response for a simple question."""
        graph = build_react_agent(mock_provider_factory, checkpointer=memory_checkpointer)

        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="What is 2+2?")],
                "iteration_count": 0,
                "error_count": 0,
                "thread_id": thread_id,
            },
            config={"configurable": {"thread_id": thread_id}},
        )

        assert result["messages"]
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        assert last_message.content  # Non-empty response

    async def test_agent_increments_iteration_count(self, mock_provider_factory, memory_checkpointer, thread_id):
        """Agent should track iteration count."""
        graph = build_react_agent(mock_provider_factory, checkpointer=memory_checkpointer)

        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Hello")],
                "iteration_count": 0,
                "error_count": 0,
                "thread_id": thread_id,
            },
            config={"configurable": {"thread_id": thread_id}},
        )

        assert result["iteration_count"] > 0

    async def test_agent_respects_max_iterations(self, mock_provider_factory, memory_checkpointer, thread_id):
        """Agent should stop at max iteration limit."""
        graph = build_react_agent(mock_provider_factory, checkpointer=memory_checkpointer)

        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Loop forever")],
                "iteration_count": 24,  # Start near limit
                "error_count": 0,
                "thread_id": thread_id,
            },
            config={
                "configurable": {"thread_id": thread_id},
                "recursion_limit": 50,
            },
        )

        assert result["iteration_count"] <= 30  # Should have stopped
```

## Tool Usage Tests

```python
class TestToolUsage:
    """Verify agent uses tools correctly."""

    async def test_agent_uses_search_tool(self, mock_provider_factory, memory_checkpointer, thread_id):
        """Agent should use search tool when asked to look something up."""
        # Configure mock LLM to request tool usage
        mock_llm = mock_provider_factory.get_default()
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="",
                tool_calls=[{"id": "call_1", "name": "search_web", "args": {"query": "test"}}],
            ),
            AIMessage(content="Based on the search results..."),
        ]

        graph = build_react_agent(mock_provider_factory, checkpointer=memory_checkpointer)
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Search for test info")],
                "iteration_count": 0,
                "error_count": 0,
                "thread_id": thread_id,
            },
            config={"configurable": {"thread_id": thread_id}},
        )

        # Verify tool was called (check intermediate messages)
        tool_messages = [m for m in result["messages"] if hasattr(m, "name")]
        assert len(tool_messages) > 0
```

## Trajectory Tests

Verify the agent's reasoning path, not just the final output.

```python
class TestAgentTrajectory:
    """Verify the agent follows expected reasoning paths."""

    async def test_agent_reasoning_path(self, mock_provider_factory, memory_checkpointer, thread_id):
        """Verify agent visits expected nodes in correct order."""
        graph = build_react_agent(mock_provider_factory, checkpointer=memory_checkpointer)

        visited_nodes = []

        async for update in graph.astream(
            {
                "messages": [HumanMessage(content="Analyze this data")],
                "iteration_count": 0,
                "error_count": 0,
                "thread_id": thread_id,
            },
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        ):
            visited_nodes.extend(update.keys())

        assert "agent" in visited_nodes
        assert visited_nodes[0] == "agent"  # Always starts with agent
```

## Resilience Tests

```python
class TestResilience:
    """Test error handling and recovery."""

    async def test_agent_handles_llm_error(self, mock_provider_factory, memory_checkpointer, thread_id):
        """Agent should handle LLM provider errors gracefully."""
        mock_llm = mock_provider_factory.get_default()
        mock_llm.ainvoke.side_effect = Exception("Provider timeout")

        graph = build_react_agent(mock_provider_factory, checkpointer=memory_checkpointer)
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Test")],
                "iteration_count": 0,
                "error_count": 0,
                "thread_id": thread_id,
            },
            config={"configurable": {"thread_id": thread_id}},
        )

        # Should have error count incremented
        assert result.get("error_count", 0) > 0

    async def test_agent_handles_tool_error(self, mock_provider_factory, memory_checkpointer, thread_id):
        """Agent should handle tool execution errors."""
        # Tool returns error string (not exception — tools should catch)
        mock_llm = mock_provider_factory.get_default()
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="",
                tool_calls=[{"id": "call_1", "name": "search_web", "args": {"query": "fail"}}],
            ),
            AIMessage(content="The search failed, but I can try another approach."),
        ]

        graph = build_react_agent(mock_provider_factory, checkpointer=memory_checkpointer)
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Search something")],
                "iteration_count": 0,
                "error_count": 0,
                "thread_id": thread_id,
            },
            config={"configurable": {"thread_id": thread_id}},
        )

        # Agent should still produce a response
        assert result["messages"][-1].content

    async def test_conversation_persists_across_invocations(self, mock_provider_factory, memory_checkpointer, thread_id):
        """Checkpointed state should persist between calls."""
        graph = build_react_agent(mock_provider_factory, checkpointer=memory_checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        # First turn
        await graph.ainvoke(
            {
                "messages": [HumanMessage(content="My name is Alice")],
                "iteration_count": 0,
                "error_count": 0,
                "thread_id": thread_id,
            },
            config=config,
        )

        # Second turn — should see previous messages
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="What is my name?")]},
            config=config,
        )

        messages = result["messages"]
        assert len(messages) > 2  # Should have both turns
```

## RAG Tests

```python
class TestRAG:
    """Test RAG retrieval and generation quality."""

    async def test_retriever_returns_relevant_docs(self, mock_retriever):
        """Retriever should return documents relevant to query."""
        docs = await mock_retriever.ainvoke("Python async programming")
        assert len(docs) > 0
        assert any("async" in doc.page_content.lower() for doc in docs)

    async def test_rag_answer_is_grounded(self, mock_llm, mock_retriever):
        """RAG answer should be grounded in retrieved documents."""
        chain = build_standard_rag(mock_llm, mock_retriever)
        answer = await chain.ainvoke("What is asyncio?")
        # Answer should reference content from mock documents
        assert answer  # Non-empty
        assert "I don't know" not in answer or len(mock_retriever.docs) == 0
```

## FastAPI Integration Tests

```python
import pytest
from httpx import ASGITransport, AsyncClient

from my_agent_service.main import app


class TestAgentAPI:
    """Integration tests for agent API endpoints."""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

    async def test_invoke_endpoint(self, client):
        """POST /api/v1/agent/invoke should return agent response."""
        response = await client.post(
            "/api/v1/agent/invoke",
            json={"message": "Hello", "thread_id": "test-thread"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "thread_id" in data

    async def test_health_endpoint(self, client):
        """GET /api/v1/health should return health status."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    async def test_invoke_validates_input(self, client):
        """POST /api/v1/agent/invoke should validate request body."""
        response = await client.post(
            "/api/v1/agent/invoke",
            json={"message": ""},  # Empty message
        )
        assert response.status_code == 422  # Validation error

    async def test_stream_endpoint(self, client):
        """POST /api/v1/agent/stream should return SSE stream."""
        async with client.stream(
            "POST",
            "/api/v1/agent/stream",
            json={"message": "Hello", "thread_id": "test-thread"},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
```

## Mock Patterns

```python
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


def mock_vector_store(documents: list[str] | None = None):
    """Create a mock vector store with predefined documents."""
    store = AsyncMock()
    docs = [Document(page_content=text, metadata={"id": str(i)}) for i, text in enumerate(documents or [])]
    store.asimilarity_search.return_value = docs
    store.aadd_documents.return_value = [str(i) for i in range(len(docs))]
    return store


def mock_embeddings():
    """Create a mock embeddings model."""
    embeddings = AsyncMock()
    embeddings.aembed_query.return_value = [0.1] * 1536
    embeddings.aembed_documents.return_value = [[0.1] * 1536]
    return embeddings
```

## Key Testing Rules

| Rule | Standard |
|------|----------|
| Checkpointer | Always use `MemorySaver` in tests — never connect to real DB |
| LLM | Always mock LLM in unit tests — use real LLM only in integration tests |
| Async | Use `pytest-asyncio` with `asyncio_mode = "auto"` |
| Coverage | Minimum 80% for agent graphs, 90% for guardrails |
| Required tests | invoke, tool usage, iteration limit, error recovery |
| Mock pattern | `AsyncMock` for all async operations |
| Thread ID | Use consistent, predictable thread IDs in tests |
