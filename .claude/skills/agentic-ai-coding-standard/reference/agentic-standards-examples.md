# Agentic AI Coding Standards — Examples & Anti-Patterns

Concrete good/bad code examples for each coding standard rule.

## Rule 1: State Typing

```python
# BAD — untyped state
def agent_node(state: dict) -> dict:
    messages = state.get("messages", [])
    return {"messages": messages + [response]}

# GOOD — TypedDict with proper annotations
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iteration_count: int

def agent_node(state: AgentState) -> dict:
    return {"messages": [response], "iteration_count": state["iteration_count"] + 1}
```

## Rule 2: Message Lists

```python
# BAD — manual message management
class BadState(TypedDict):
    messages: list  # No type, no reducer

def node(state):
    return {"messages": state["messages"] + [response]}  # Manual append

# GOOD — add_messages annotation handles merging
class GoodState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def node(state):
    return {"messages": [response]}  # add_messages handles the merge
```

## Rule 3: Loop Protection

```python
# BAD — no iteration limit
def should_continue(state):
    if state["messages"][-1].tool_calls:
        return "tools"
    return END
# Can loop forever if LLM always requests tools

# GOOD — iteration limit check
MAX_ITERATIONS = 25

def should_continue(state: AgentState) -> str:
    if state["iteration_count"] >= MAX_ITERATIONS:
        logger.warning("max_iterations_reached", count=state["iteration_count"])
        return END
    if isinstance(state["messages"][-1], AIMessage) and state["messages"][-1].tool_calls:
        return "tools"
    return END
```

## Rule 4: Tool Functions

```python
# BAD — no docstring, no error handling, wrong return type
@tool
def search(q):
    return requests.get(f"https://api.example.com/search?q={q}").json()

# GOOD — docstring, error handling, returns string
@tool
def search_web(query: str) -> str:
    """Search the web for current information about a topic.

    Args:
        query: Specific search query. Be precise for better results.

    Returns:
        JSON string of search results.
    """
    try:
        results = _call_search_api(query)
        logger.info("tool_search", query=query, result_count=len(results))
        return json.dumps(results)
    except Exception as e:
        logger.error("tool_search_failed", query=query, error=str(e))
        return f"Search failed: {e}"
```

## Rule 5: LLM Instantiation

```python
# BAD — inline instantiation in node
async def agent_node(state):
    llm = ChatAnthropic(model="claude-sonnet-4-20250514", api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}

# GOOD — factory function, injected
def build_react_agent(provider_factory: LLMProviderFactory, checkpointer=None):
    llm = provider_factory.get_default().bind_tools(tools)

    async def agent_node(state: AgentState) -> dict:
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response], "iteration_count": state["iteration_count"] + 1}
    ...
```

## Rule 6: Temperature

```python
# BAD — high temperature for factual tasks
llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=1.0)
# Causes inconsistent, potentially hallucinated factual answers

# GOOD — temperature matches task type
factual_llm = factory.get_model("claude-sonnet-4-20250514", temperature=0)  # Facts, classification, routing
creative_llm = factory.get_model("claude-sonnet-4-20250514", temperature=0.7)  # Creative writing only
```

## Rule 7: Checkpointing

```python
# BAD — MemorySaver in production
graph = build_react_agent(factory, checkpointer=MemorySaver())
# State is lost on restart!

# GOOD — PostgresSaver in production
checkpointer = AsyncPostgresSaver.from_conn_string(settings.checkpoint_db_uri)
await checkpointer.setup()
graph = build_react_agent(factory, checkpointer=checkpointer)
```

## Rule 8: Error Handling

```python
# BAD — swallowed exception
async def agent_node(state):
    try:
        response = await llm.ainvoke(state["messages"])
    except Exception:
        pass  # Silently swallowed!
    return {"messages": []}

# BAD — exception with empty fallback
async def agent_node(state):
    try:
        response = await llm.ainvoke(state["messages"])
    except Exception:
        return {"messages": []}  # Silent empty return

# GOOD — logged, visible error state
async def agent_node(state: AgentState) -> dict:
    try:
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response], "iteration_count": state["iteration_count"] + 1}
    except Exception as e:
        logger.error("agent_node_failed", error=str(e), thread_id=state.get("thread_id"))
        return {
            "messages": [AIMessage(content=f"I encountered an error: {e}")],
            "error_count": state.get("error_count", 0) + 1,
            "iteration_count": state["iteration_count"] + 1,
        }
```

## Rule 9: Naming

```python
# BAD — inconsistent naming
def my_agent(state): ...           # Not build_*_agent()
def process(state): ...            # Not verb_node()
class State(TypedDict): ...        # Not *State

# GOOD — consistent naming
def build_react_agent(factory, checkpointer=None): ...
def retrieve_node(state: RAGState) -> dict: ...
class RAGState(TypedDict): ...
```

## Rule 10: Configuration

```python
# BAD — os.getenv with silent defaults
model = os.getenv("MODEL", "claude-sonnet-4-20250514")  # Fails silently if wrong
api_key = os.getenv("API_KEY", "")  # Empty string → cryptic errors later

# GOOD — pydantic-settings with fail-fast validation
class Settings(BaseSettings):
    anthropic_api_key: str  # Required — app crashes if missing

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_key(cls, v):
        if not v.startswith("sk-ant-"):
            raise ValueError("Invalid Anthropic API key format")
        return v

settings = Settings()  # Fails immediately if env vars are wrong
```

## Rule 14: Secrets

```python
# BAD — API key in logs
logger.info(f"Using API key: {settings.anthropic_api_key}")
logger.info("Config", extra={"api_key": settings.anthropic_api_key})

# BAD — PII in LangSmith trace metadata
config = {"metadata": {"user_email": "john@example.com"}}

# GOOD — redacted logging, no PII in traces
logger.info("llm_configured", provider="anthropic", key_prefix=settings.anthropic_api_key[:10] + "...")
config = {"metadata": {"user_id": "usr_abc123"}}  # Use opaque IDs
```

## Anti-Patterns Table

| # | Anti-Pattern | Problem | Fix |
|---|-------------|---------|-----|
| 1 | `dict[str, Any]` for state | No type safety, IDE can't help | Use `TypedDict` |
| 2 | No `add_messages` | Messages overwrite instead of merge | Use `Annotated[list, add_messages]` |
| 3 | No iteration counter | Infinite loops | Add `iteration_count` + check in routing |
| 4 | `@tool` without docstring | LLM can't decide when to use tool | Always add descriptive docstring |
| 5 | Inline `ChatAnthropic()` | Scattered config, no fallback | Use `LLMProviderFactory` |
| 6 | `temperature=1.0` for facts | Hallucination | `temperature=0` for factual |
| 7 | `MemorySaver` in production | State lost on restart | `PostgresSaver` |
| 8 | `except: pass` | Silent failures | Log + return error state |
| 9 | `os.getenv()` for required vars | Late, cryptic failures | pydantic-settings + validators |
| 10 | API keys in logs | Security breach | Redact, use prefixes only |
| 11 | Sync `def` in FastAPI | Blocks event loop | `async def` for all I/O |
| 12 | No `thread_id` in config | No conversation persistence | Always pass `thread_id` |
