# Agentic AI — Error Recovery & Design Decisions

Error recovery patterns and architectural design decisions for LangGraph agents.

## Pattern 6: Error Recovery Agent

Built-in retry, fallback, and graceful degradation.

```python
from __future__ import annotations

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph

from ...core.exceptions import LLMProviderError
from ...core.logging import get_logger

logger = get_logger(__name__)

MAX_ERRORS = 3


def build_resilient_agent(provider_factory, checkpointer=None) -> StateGraph:
    """Agent with built-in error recovery and fallback."""

    primary_llm = provider_factory.get("anthropic")
    fallback_llm = provider_factory.get("openai")

    async def agent_node(state: AgentState) -> dict:
        """Try primary LLM, fall back to secondary on failure."""
        error_count = state.get("error_count", 0)

        try:
            # Use fallback after repeated errors
            llm = fallback_llm if error_count >= 2 else primary_llm
            response = await llm.ainvoke(state["messages"])
            return {
                "messages": [response],
                "iteration_count": state["iteration_count"] + 1,
                "error_count": 0,  # Reset on success
            }

        except LLMProviderError as e:
            logger.warning("llm_error", error=str(e), error_count=error_count + 1)
            return {
                "messages": [AIMessage(content=f"Retrying after error: {e}")],
                "error_count": error_count + 1,
                "iteration_count": state["iteration_count"] + 1,
            }

    def should_continue(state: AgentState) -> str:
        """Check error budget and iteration limit."""
        if state.get("error_count", 0) >= MAX_ERRORS:
            logger.error("error_budget_exhausted")
            return "fallback"
        if state["iteration_count"] >= 25:
            return END
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    async def fallback_node(state: AgentState) -> dict:
        """Graceful degradation — return a helpful error message."""
        return {
            "messages": [AIMessage(
                content="I'm experiencing technical difficulties. "
                "Please try again in a moment or rephrase your request."
            )],
        }

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("fallback", fallback_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")
    graph.add_edge("fallback", END)

    return graph.compile(checkpointer=checkpointer)
```

## Key Design Decisions

| Decision | Recommendation | Reason |
|----------|---------------|--------|
| State typing | Always `TypedDict` | Type safety, IDE support, LangGraph compatibility |
| Routing | `Command` pattern | Cleaner than conditional edges, co-locates routing logic with node |
| Error handling | Error counter + fallback node | Prevents infinite retry loops, graceful degradation |
| Checkpointing | Always configure | Enables conversation memory, crash recovery, HITL |
| Iteration limit | Check in routing function | Hard safety boundary against infinite loops |
| LLM instantiation | Factory function | Centralizes config, enables fallback chains |
