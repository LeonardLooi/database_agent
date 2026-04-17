# Agentic AI — Advanced Agent Patterns

Advanced LangGraph agent patterns — hierarchical supervision, Command-based routing, and sub-graph composition.

## Pattern 3: Hierarchical Supervisor

A supervisor delegates to specialists and controls quality.

**File:** `src/<service>/agents/graphs/supervisor_agent.py`

```python
from __future__ import annotations

from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from ...core.logging import get_logger
from ...llm.providers import LLMProviderFactory
from ..state import MultiAgentState

logger = get_logger(__name__)

SUPERVISOR_PROMPT = """You are a supervisor managing a team of specialists.
Available specialists: {specialists}

For each user request:
1. Decide which specialist should handle it
2. Review the specialist's output
3. Either approve (respond to user) or request revision

Respond with JSON: {{"route": "specialist_name"}} or {{"route": "FINISH", "response": "final answer"}}
"""


def build_supervisor_agent(
    provider_factory: LLMProviderFactory,
    checkpointer=None,
) -> StateGraph:
    """Build a hierarchical supervisor agent.

    The supervisor decides which specialist to invoke, reviews output,
    and iterates until quality is sufficient.
    """
    llm = provider_factory.get_default()
    specialists = ["researcher", "coder", "reviewer"]

    async def supervisor_node(state: MultiAgentState) -> Command:
        """Supervisor decides next action based on current state."""
        response = await llm.with_structured_output(SupervisorDecision).ainvoke([
            SystemMessage(content=SUPERVISOR_PROMPT.format(specialists=specialists)),
            *state["messages"],
        ])

        if response.route == "FINISH":
            return Command(
                goto=END,
                update={
                    "messages": [AIMessage(content=response.response)],
                    "iteration_count": state["iteration_count"] + 1,
                },
            )

        return Command(
            goto=response.route,
            update={"iteration_count": state["iteration_count"] + 1},
        )

    async def researcher_node(state: MultiAgentState) -> Command:
        """Research specialist — returns to supervisor for review."""
        response = await llm.ainvoke([
            SystemMessage(content="You are a research specialist. Provide thorough, factual research."),
            *state["messages"],
        ])
        return Command(
            goto="supervisor",
            update={"messages": [response]},
        )

    async def coder_node(state: MultiAgentState) -> Command:
        """Coding specialist — returns to supervisor for review."""
        response = await llm.ainvoke([
            SystemMessage(content="You are a coding specialist. Write clean, tested, production code."),
            *state["messages"],
        ])
        return Command(
            goto="supervisor",
            update={"messages": [response]},
        )

    async def reviewer_node(state: MultiAgentState) -> Command:
        """Review specialist — returns to supervisor with feedback."""
        response = await llm.ainvoke([
            SystemMessage(content="You are a code reviewer. Review for correctness, security, and style."),
            *state["messages"],
        ])
        return Command(
            goto="supervisor",
            update={"messages": [response]},
        )

    # --- Graph Assembly ---

    graph = StateGraph(MultiAgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("coder", coder_node)
    graph.add_node("reviewer", reviewer_node)

    graph.set_entry_point("supervisor")
    # Edges are handled by Command returns — no explicit conditional edges needed

    return graph.compile(checkpointer=checkpointer)


# Pydantic model for structured supervisor output
from pydantic import BaseModel, Field


class SupervisorDecision(BaseModel):
    """Structured output for supervisor routing decisions."""

    route: Literal["researcher", "coder", "reviewer", "FINISH"]
    response: str = Field(default="", description="Final response when route is FINISH")
```

## Pattern 4: LangGraph Command Pattern

The preferred routing pattern in LangGraph — cleaner than conditional edges for complex flows.

```python
from langgraph.types import Command

# Instead of conditional edges, nodes return Command objects

async def triage_node(state: AgentState) -> Command:
    """Route using Command pattern — cleaner than conditional edges."""
    analysis = await llm.ainvoke([
        SystemMessage(content="Classify this request: technical, billing, or general"),
        *state["messages"],
    ])

    category = parse_category(analysis.content)

    return Command(
        goto=category,  # Route to the appropriate node
        update={
            "messages": [analysis],
            "iteration_count": state["iteration_count"] + 1,
        },
    )

# Graph setup — no conditional edges needed
graph = StateGraph(AgentState)
graph.add_node("triage", triage_node)
graph.add_node("technical", technical_node)
graph.add_node("billing", billing_node)
graph.add_node("general", general_node)
graph.set_entry_point("triage")
# Command handles all routing — just add edges back to triage if needed
graph.add_edge("technical", END)
graph.add_edge("billing", END)
graph.add_edge("general", END)
```

## Pattern 5: Sub-Graph Composition

Reusable sub-graphs composed into a larger workflow.

```python
from langgraph.graph import StateGraph, END


def build_rag_subgraph(provider_factory) -> StateGraph:
    """Reusable RAG sub-graph that can be embedded in any parent graph."""
    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("grade", grade_documents_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_conditional_edges("grade", grade_router)
    graph.add_edge("generate", END)

    return graph.compile()


def build_parent_agent(provider_factory, checkpointer=None) -> StateGraph:
    """Parent graph that uses RAG as a sub-graph."""
    rag_graph = build_rag_subgraph(provider_factory)

    async def rag_node(state: AgentState) -> dict:
        """Delegate to RAG sub-graph."""
        result = await rag_graph.ainvoke({
            "messages": state["messages"],
            "query": state["messages"][-1].content,
            "documents": [],
            "generation": "",
            "is_grounded": False,
            "iteration_count": 0,
            "error_count": 0,
            "thread_id": state["thread_id"],
        })
        return {"messages": result["messages"]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("rag", rag_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", route_agent)
    graph.add_edge("rag", "agent")
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer)
```
