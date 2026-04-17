# Error Handling Patterns

## Agent Errors
```python
# In graph nodes — return error state, never raise
def agent_node(state: AgentState) -> AgentState:
    try:
        response = llm.invoke(state["messages"])
        return {"messages": [response], "iteration_count": state["iteration_count"] + 1}
    except Exception as e:
        logger.error("agent_node_failed", error=str(e), thread_id=state.get("thread_id"))
        return {"messages": [AIMessage(content=f"I encountered an error: {e}")], "error_count": state.get("error_count", 0) + 1}
```

## Tool Errors
```python
@tool
def search_database(query: str) -> str:
    """Search the database for relevant records."""
    try:
        results = db.search(query)
        return json.dumps(results)
    except DatabaseError as e:
        logger.error("tool_search_failed", error=str(e), query=query)
        return f"Error searching database: {e}"
```

## LLM Provider Errors
```python
# Use fallback chain in provider factory
async def invoke_with_fallback(messages: list, providers: list[BaseChatModel]) -> AIMessage:
    for provider in providers:
        try:
            return await provider.ainvoke(messages)
        except Exception as e:
            logger.warning("provider_failed", provider=type(provider).__name__, error=str(e))
    raise LLMProviderError("All providers failed")
```

## API Errors
```python
@router.post("/api/v1/agent/invoke")
async def invoke_agent(request: AgentRequest, graph = Depends(get_graph)):
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=request.message)]},
            config={"configurable": {"thread_id": request.thread_id}},
        )
        return AgentResponse(message=result["messages"][-1].content)
    except LLMProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error("invoke_failed", error=str(e), thread_id=request.thread_id)
        raise HTTPException(status_code=500, detail="Agent invocation failed")
```
