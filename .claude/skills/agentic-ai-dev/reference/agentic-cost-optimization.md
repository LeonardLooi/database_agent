# Agentic AI Cost Optimization

Strategies for managing and reducing LLM costs in production agent systems.

## Model Selection Checklist

Before choosing a model, answer these questions:

| Question | If YES | If NO |
|----------|--------|-------|
| Does it need complex reasoning? | Use `claude-sonnet-4` or `gpt-4o` | Use `claude-haiku-3.5` or `gpt-4o-mini` |
| Does it need structured output? | Any model with `.with_structured_output()` | Same |
| Is it a routing/classification task? | Use cheapest model (`haiku`, `4o-mini`) | N/A |
| Does latency matter? | Use faster models (`haiku`, `4o-mini`, `flash`) | Use best quality model |
| Is it user-facing? | Balance quality + speed | Optimize for cost |

## Cost Comparison (per 1M tokens, as of 2025)

| Model | Input | Output | Quality | Speed |
|-------|-------|--------|---------|-------|
| claude-opus-4 | $15.00 | $75.00 | Best | Slow |
| claude-sonnet-4 | $3.00 | $15.00 | Great | Medium |
| claude-haiku-3.5 | $0.80 | $4.00 | Good | Fast |
| gpt-4o | $2.50 | $10.00 | Great | Medium |
| gpt-4o-mini | $0.15 | $0.60 | Good | Fast |
| gemini-3.1-flash | $0.10 | $0.40 | Good | Fast |

## Prompt Optimization Strategies

### 1. Reduce System Prompt Size

```python
# BAD: Verbose system prompt (2000+ tokens every call)
SYSTEM_PROMPT = """You are a helpful assistant. You should always be polite and
helpful. When answering questions, provide detailed and comprehensive responses.
Consider multiple perspectives and provide balanced viewpoints..."""  # 500 words

# GOOD: Concise system prompt
SYSTEM_PROMPT = """Expert assistant. Answer accurately and concisely.
Tools: search (web), query (database), calculate (math).
Rules: Use tools for facts. Say "I don't know" if unsure."""  # 30 words
```

### 2. Use Prompt Caching (Anthropic)

```python
from langchain_core.messages import SystemMessage

# Cache long prompts — 90% cost reduction on cached portion
cached_prompt = SystemMessage(content=[{
    "type": "text",
    "text": LONG_SYSTEM_PROMPT,  # Only pay full price once
    "cache_control": {"type": "ephemeral"},
}])
```

### 3. Minimize Context Window Usage

```python
def optimize_context(messages: list, max_tokens: int = 2000) -> list:
    """Keep only essential context to reduce token usage."""
    # Always keep: system prompt + last 3 messages
    system = [m for m in messages if m.type == "system"]
    recent = messages[-3:] if len(messages) > 3 else messages

    # Summarize older messages instead of including full history
    if len(messages) > 6:
        # Include summary instead of full history
        older = messages[len(system):-3]
        summary = f"[Previous {len(older)} messages summarized: User discussed {extract_topics(older)}]"
        return [*system, HumanMessage(content=summary), *recent]

    return messages
```

## Caching Strategies

### Embedding Cache

```python
import hashlib
import json


class EmbeddingCache:
    """Cache embeddings to avoid re-computing for identical inputs."""

    def __init__(self, redis_client):
        self._redis = redis_client
        self._ttl = 86400 * 7  # 7 days

    async def get_or_compute(self, text: str, embeddings_model) -> list[float]:
        """Return cached embedding or compute and cache."""
        cache_key = f"emb:{hashlib.sha256(text.encode()).hexdigest()}"

        # Check cache
        cached = await self._redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Compute and cache
        embedding = await embeddings_model.aembed_query(text)
        await self._redis.setex(cache_key, self._ttl, json.dumps(embedding))
        return embedding
```

### Response Cache

```python
class ResponseCache:
    """Cache LLM responses for identical inputs.

    Useful for:
    - Classification tasks (same input → same output)
    - FAQ-style questions
    - Deterministic operations (temperature=0)
    """

    def __init__(self, redis_client, ttl: int = 3600):
        self._redis = redis_client
        self._ttl = ttl

    async def get_or_invoke(self, llm, messages: list, cache_key: str | None = None) -> str:
        """Return cached response or invoke LLM."""
        if cache_key is None:
            content = "".join(m.content for m in messages)
            cache_key = f"llm:{hashlib.sha256(content.encode()).hexdigest()}"

        cached = await self._redis.get(cache_key)
        if cached:
            logger.info("cache_hit", key=cache_key[:20])
            return cached.decode()

        response = await llm.ainvoke(messages)
        await self._redis.setex(cache_key, self._ttl, response.content)
        logger.info("cache_miss", key=cache_key[:20])
        return response.content
```

## Architecture Patterns for Cost Reduction

### 1. Minimize LLM Calls

```python
# BAD: Multiple LLM calls for simple logic
category = await llm.ainvoke("Classify this request...")  # Call 1
response = await llm.ainvoke(f"Handle this {category} request...")  # Call 2

# GOOD: Single call with combined instructions
response = await llm.ainvoke(
    "Classify this request and respond appropriately. "
    "Format: Category: [category]\nResponse: [your response]"
)
```

### 2. Batch Similar Operations

```python
# BAD: Grade documents one at a time (N LLM calls)
for doc in documents:
    grade = await llm.ainvoke(f"Is this relevant? {doc}")

# GOOD: Grade all documents in one call (1 LLM call)
all_docs = "\n---\n".join(f"[{i}] {doc}" for i, doc in enumerate(documents))
grades = await llm.with_structured_output(BatchGrades).ainvoke(
    f"Grade the relevance of each document:\n{all_docs}"
)
```

### 3. Early Termination

```python
def should_continue(state: AgentState) -> str:
    """Stop early when we have a good enough answer."""
    if state.get("confidence_score", 0) > 0.9:
        return END  # Don't spend more tokens if we're confident

    if state["iteration_count"] >= 3 and not state.get("new_info_found"):
        return END  # Stop if we're not finding new information

    return "agent"
```

### 4. Use Cheapest Model Per Task

```python
# Classification: use cheapest model
classifier = provider_factory.get("anthropic", "fast")  # haiku

# Generation: use balanced model
generator = provider_factory.get("anthropic", "balanced")  # sonnet

# Complex reasoning: use best model (sparingly)
reasoner = provider_factory.get("anthropic", "powerful")  # opus
```

## Cost Estimation Calculator

```python
from dataclasses import dataclass


@dataclass
class CostEstimate:
    """Estimated cost for an operation."""
    input_tokens: int
    output_tokens: int
    model: str
    cost_usd: float
    cached_tokens: int = 0
    cache_savings_usd: float = 0.0


def estimate_agent_session_cost(
    model: str = "claude-sonnet-4-20250514",
    turns: int = 5,
    avg_input_per_turn: int = 1500,
    avg_output_per_turn: int = 500,
    tools_per_turn: int = 1,
    tool_input_tokens: int = 200,
    tool_output_tokens: int = 300,
) -> CostEstimate:
    """Estimate total cost for a multi-turn agent session.

    Accounts for accumulating context (each turn includes all previous messages).
    """
    total_input = 0
    total_output = 0

    for turn in range(turns):
        # Input grows with conversation history
        turn_input = avg_input_per_turn * (turn + 1)
        turn_output = avg_output_per_turn

        # Tool calls add to both input and output
        turn_input += tools_per_turn * tool_input_tokens
        turn_output += tools_per_turn * tool_output_tokens

        total_input += turn_input
        total_output += turn_output

    cost = estimate_cost(model, total_input, total_output)

    return CostEstimate(
        input_tokens=total_input,
        output_tokens=total_output,
        model=model,
        cost_usd=cost,
    )
```

## Budget Caps and Alerting

```python
from ..observability.metrics import LLM_COST


class BudgetManager:
    """Enforce cost budgets per thread, user, and globally."""

    def __init__(
        self,
        per_request_limit: float = 0.50,
        per_session_limit: float = 5.00,
        daily_limit: float = 100.00,
    ):
        self._per_request = per_request_limit
        self._per_session = per_session_limit
        self._daily = daily_limit
        self._session_costs: dict[str, float] = {}
        self._daily_cost: float = 0.0

    def check_budget(self, thread_id: str, estimated_cost: float) -> bool:
        """Check if the estimated cost is within budget."""
        if estimated_cost > self._per_request:
            logger.warning("budget_exceeded_per_request", thread_id=thread_id, cost=estimated_cost)
            return False

        session_cost = self._session_costs.get(thread_id, 0.0)
        if session_cost + estimated_cost > self._per_session:
            logger.warning("budget_exceeded_per_session", thread_id=thread_id, total=session_cost + estimated_cost)
            return False

        if self._daily_cost + estimated_cost > self._daily:
            logger.error("budget_exceeded_daily", total=self._daily_cost + estimated_cost)
            return False

        return True

    def record_cost(self, thread_id: str, cost: float, model: str) -> None:
        """Record actual cost after invocation."""
        self._session_costs[thread_id] = self._session_costs.get(thread_id, 0.0) + cost
        self._daily_cost += cost
        LLM_COST.labels(provider="all", model=model).inc(cost)
```

## Key Rules

| Rule | Standard |
|------|----------|
| Model selection | Cheapest model that meets quality requirements |
| Temperature | `0` for deterministic tasks (enables caching) |
| Caching | Cache embeddings (7d), responses for FAQ (1h) |
| Context | Trim/summarize history to minimize input tokens |
| Batching | Batch similar operations into single LLM calls |
| Budget | Set per-request, per-session, and daily limits |
| Monitoring | Track `llm_cost_usd_total` metric, alert on budget |
| Prompt caching | Use Anthropic `cache_control` for long system prompts |
| Dashboard budgets | Set spending alerts in provider dashboards (Anthropic Console, OpenAI Usage, GCP Billing) — code-level `BudgetManager` is defense-in-depth, not a replacement for provider-level hard caps and email/PagerDuty alerts |
| Quota limits | Configure per-project rate limits and monthly spend caps in each provider's console before deploying to production |

---

## CAG — Cache Augmented Generation

**CAG** pre-loads documents into the prompt context once (with Anthropic prompt caching) instead of retrieving them dynamically on every query. Use when your document set is fixed, small enough to fit in context (<200K tokens), and queried repeatedly.

### CAG vs RAG Decision

```
Document set size?
├── Small (< 200K tokens, fits in one prompt)
│   ├── Queried repeatedly? → CAG (cache the full set once)
│   └── Queried once/rarely? → Direct context (no caching needed)
└── Large (> 200K tokens, does not fit)
    └── → RAG (embedding retrieval)
```

**CAG advantages over RAG:**
- No retrieval latency (documents already in context)
- No chunking errors or missed relevant sections
- No embedding model cost
- After first query, 90% cost reduction via Anthropic prompt caching

**CAG disadvantages vs RAG:**
- Limited to documents that fit in context window
- Full document cost on cache miss (first query or cache expiry)
- Not suitable for frequently updated documents

---

### CAG Implementation — LangGraph

```python
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

def load_documents_as_cached_context(doc_paths: list[str]) -> str:
    """Load documents into a single cached context block."""
    docs = []
    for path in doc_paths:
        content = Path(path).read_text()
        docs.append(f"=== {path} ===\n{content}")
    return "\n\n".join(docs)


def build_cag_messages(documents_context: str, question: str) -> list:
    """
    Structure: system (cached role) + human (cached docs) + human (question)
    Anthropic caches the first two blocks — question varies each call.
    """
    return [
        # Block 1: cached system prompt
        SystemMessage(content={
            "type": "text",
            "text": "You are a precise document analyst. Answer questions based ONLY on the provided documents. If the answer is not in the documents, say 'Not found in documents.'",
            "cache_control": {"type": "ephemeral"}
        }),
        # Block 2: cached document context (largest block — highest cache value)
        HumanMessage(content=[{
            "type": "text",
            "text": f"Documents:\n\n{documents_context}",
            "cache_control": {"type": "ephemeral"}
        }]),
        # Block 3: NOT cached — varies per query
        HumanMessage(content=f"Question: {question}")
    ]


# Initialize once at startup — reuse across requests
DOCS_CONTEXT = load_documents_as_cached_context([
    "docs/api-reference.md",
    "docs/architecture.md",
    "docs/runbook.md"
])

llm = ChatAnthropic(model="claude-sonnet-4-6")

def cag_node(state: AgentState) -> AgentState:
    """CAG node — documents cached, only question varies."""
    messages = build_cag_messages(DOCS_CONTEXT, state["question"])
    response = llm.invoke(messages)
    return {"answer": response.content}
```

**Cost profile:**
- First query: full document tokens billed (cache population)
- Subsequent queries: ~90% reduction (only question tokens billed at full rate)
- Cache TTL: 5 minutes (Anthropic ephemeral) — reset with each query within TTL

---

### CAG Implementation — Google ADK

```python
from google.adk.agents import LlmAgent
from pathlib import Path

def build_cag_agent(doc_paths: list[str]) -> LlmAgent:
    """Build an ADK agent with documents pre-loaded in instruction."""
    docs = []
    for path in doc_paths:
        content = Path(path).read_text()
        docs.append(f"=== {path} ===\n{content}")

    document_block = "\n\n".join(docs)

    # For ADK: use Gemini context caching for large document sets
    # docs: https://ai.google.dev/gemini-api/docs/caching
    return LlmAgent(
        name="cag_agent",
        model="gemini-3.1-flash",  # 1M token context — fits large document sets
        instruction=f"""You are a precise document analyst.
Answer questions based ONLY on the documents below.
If the answer is not in the documents, respond: "Not found in documents."

DOCUMENTS:
{document_block}"""
    )


# Initialize once — reuse agent across requests
cag_agent = build_cag_agent([
    "docs/api-reference.md",
    "docs/architecture.md",
    "docs/runbook.md"
])
```

**ADK Note:** For very large document sets with Gemini, use the Gemini Context Caching API (`google-genai` SDK) instead of embedding documents in instruction. See `gemini-api-dev` skill for context caching patterns.

---

### When CAG Fails — Fall Back to RAG

```python
def should_use_cag(doc_paths: list[str], token_limit: int = 180_000) -> bool:
    """Check if documents fit in context for CAG."""
    total_chars = sum(len(Path(p).read_text()) for p in doc_paths)
    # Rough estimate: 1 token ≈ 4 characters
    estimated_tokens = total_chars // 4
    return estimated_tokens <= token_limit


# Decision at startup
if should_use_cag(DOC_PATHS):
    agent = build_cag_agent(DOC_PATHS)
else:
    # Fall back to RAG pipeline
    agent = build_rag_agent(DOC_PATHS)
```
