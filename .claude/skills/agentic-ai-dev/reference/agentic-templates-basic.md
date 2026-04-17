# Agentic AI — Basic Agent Patterns

Foundational LangGraph agent patterns with typed state, proper error handling, iteration limits, and checkpointing.

## Pattern 1: ReAct Agent

The foundational agent pattern — reason and act in a loop with tool use.

**File:** `src/<service>/agents/graphs/react_agent.py`

```python
from __future__ import annotations

from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from ...core.logging import get_logger
from ...llm.providers import LLMProviderFactory
from ..state import AgentState
from ..tools.search import search_tool, calculator_tool

logger = get_logger(__name__)

MAX_ITERATIONS = 25


def build_react_agent(
    provider_factory: LLMProviderFactory,
    checkpointer=None,
) -> StateGraph:
    """Build a ReAct agent graph with tool use.

    Args:
        provider_factory: Factory for LLM provider instances.
        checkpointer: LangGraph checkpointer for state persistence.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    tools = [search_tool, calculator_tool]
    llm = provider_factory.get_default().bind_tools(tools)

    # --- Nodes ---

    async def agent_node(state: AgentState) -> dict:
        """Core reasoning node — invoke LLM with current state."""
        logger.info("agent_reasoning", iteration=state["iteration_count"])
        response = await llm.ainvoke(state["messages"])
        return {
            "messages": [response],
            "iteration_count": state["iteration_count"] + 1,
        }

    # --- Routing ---

    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        """Route based on whether the LLM wants to use tools or is done."""
        if state["iteration_count"] >= MAX_ITERATIONS:
            logger.warning("max_iterations_reached", count=state["iteration_count"])
            return END

        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    # --- Graph Assembly ---

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer)
```

## Pattern 2: Multi-Agent Collaborative

Multiple specialist agents collaborate on complex tasks with shared state.

**File:** `src/<service>/agents/graphs/multi_agent.py`

```python
from __future__ import annotations

from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from ...core.logging import get_logger
from ...llm.providers import LLMProviderFactory
from ..state import MultiAgentState

logger = get_logger(__name__)


def build_multi_agent(
    provider_factory: LLMProviderFactory,
    checkpointer=None,
) -> StateGraph:
    """Build a multi-agent collaborative graph.

    Architecture:
        router -> [researcher | analyst | writer] -> synthesizer -> END

    Each specialist processes the task independently, then the synthesizer
    combines their outputs into a final response.
    """
    llm = provider_factory.get_default()

    # --- Specialist Nodes ---

    async def router_node(state: MultiAgentState) -> dict:
        """Analyze the task and create a plan for specialists."""
        response = await llm.ainvoke([
            SystemMessage(content="You are a task router. Analyze the request and create a plan. "
                          "Decide which specialists are needed: researcher, analyst, writer."),
            *state["messages"],
        ])
        # Parse the plan from the response
        plan = ["researcher", "analyst", "writer"]  # Simplified; parse from LLM response
        return {
            "messages": [response],
            "task_plan": plan,
            "current_agent": "researcher",
            "iteration_count": state["iteration_count"] + 1,
        }

    async def researcher_node(state: MultiAgentState) -> dict:
        """Research specialist — gathers information and facts."""
        response = await llm.ainvoke([
            SystemMessage(content="You are a research specialist. Gather relevant facts and information."),
            *state["messages"],
        ])
        outputs = {**state.get("agent_outputs", {}), "researcher": response.content}
        completed = [*state.get("completed_tasks", []), "researcher"]
        return {
            "messages": [response],
            "agent_outputs": outputs,
            "completed_tasks": completed,
            "iteration_count": state["iteration_count"] + 1,
        }

    async def analyst_node(state: MultiAgentState) -> dict:
        """Analysis specialist — identifies patterns and insights."""
        context = state.get("agent_outputs", {}).get("researcher", "")
        response = await llm.ainvoke([
            SystemMessage(content=f"You are an analysis specialist. Research context:\n{context}"),
            *state["messages"],
        ])
        outputs = {**state.get("agent_outputs", {}), "analyst": response.content}
        completed = [*state.get("completed_tasks", []), "analyst"]
        return {
            "messages": [response],
            "agent_outputs": outputs,
            "completed_tasks": completed,
            "iteration_count": state["iteration_count"] + 1,
        }

    async def writer_node(state: MultiAgentState) -> dict:
        """Writing specialist — produces the final written output."""
        research = state.get("agent_outputs", {}).get("researcher", "")
        analysis = state.get("agent_outputs", {}).get("analyst", "")
        response = await llm.ainvoke([
            SystemMessage(content=f"You are a writing specialist.\nResearch:\n{research}\nAnalysis:\n{analysis}"),
            *state["messages"],
        ])
        outputs = {**state.get("agent_outputs", {}), "writer": response.content}
        completed = [*state.get("completed_tasks", []), "writer"]
        return {
            "messages": [response],
            "agent_outputs": outputs,
            "completed_tasks": completed,
            "iteration_count": state["iteration_count"] + 1,
        }

    async def synthesizer_node(state: MultiAgentState) -> dict:
        """Combine all specialist outputs into a coherent final response."""
        all_outputs = "\n\n".join(
            f"=== {agent} ===\n{output}"
            for agent, output in state.get("agent_outputs", {}).items()
        )
        response = await llm.ainvoke([
            SystemMessage(content=f"Synthesize these specialist outputs into one coherent response:\n{all_outputs}"),
            HumanMessage(content=state["messages"][0].content),
        ])
        return {
            "messages": [response],
            "iteration_count": state["iteration_count"] + 1,
        }

    # --- Routing ---

    def route_next_specialist(state: MultiAgentState) -> str:
        """Route to the next incomplete specialist or to synthesizer."""
        plan = state.get("task_plan", [])
        completed = state.get("completed_tasks", [])
        for task in plan:
            if task not in completed:
                return task
        return "synthesizer"

    # --- Graph Assembly ---

    graph = StateGraph(MultiAgentState)
    graph.add_node("router", router_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("writer", writer_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges("router", route_next_specialist)
    graph.add_conditional_edges("researcher", route_next_specialist)
    graph.add_conditional_edges("analyst", route_next_specialist)
    graph.add_conditional_edges("writer", route_next_specialist)
    graph.add_edge("synthesizer", END)

    return graph.compile(checkpointer=checkpointer)
```
