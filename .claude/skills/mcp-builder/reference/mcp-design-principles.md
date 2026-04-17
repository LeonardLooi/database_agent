# MCP Server Best Practices

## Quick Reference

### Server Naming
- **Python**: `{service}_mcp` (e.g., `slack_mcp`)
- **Node/TypeScript**: `{service}-mcp-server` (e.g., `slack-mcp-server`)

### Tool Naming
- Use snake_case with service prefix
- Format: `{service}_{action}_{resource}`
- Example: `slack_send_message`, `github_create_issue`

### Response Formats
- Support both JSON and Markdown formats
- JSON for programmatic processing
- Markdown for human readability

### Pagination
- Always respect `limit` parameter
- Return `has_more`, `next_offset`, `total_count`
- Default to 20-50 items

### Agent-Directive Responses
- Every tool response MUST include `next_actions` (machine-readable) and `suggestion` (human-readable)
- Use `formatAgentResponse<T>()` helper (see agent-design-patterns.md)
- Include `context` for state chaining between tool calls

### Tool Count Limits
- IDEAL: 10-15 tools — optimal agent performance
- ACCEPTABLE: 16-25 tools — manageable with good descriptions
- WARNING: 26-30 tools — consider consolidation
- CRITICAL: 31+ tools — agent decision paralysis

### Transport
- **Streamable HTTP**: For remote servers, multi-client scenarios
- **stdio**: For local integrations, command-line tools
- Avoid SSE (deprecated in favor of streamable HTTP)

---

## Primitives Decision Framework

MCP has three core primitives. Choosing the right one affects agent performance:

| Primitive | Controlled By | Best For | Examples |
|-----------|---------------|----------|----------|
| **Tools** | Model (LLM invokes) | Actions, dynamic queries, side effects | `create_issue`, `search_users`, `send_email` |
| **Resources** | Application (context injection) | Static data, docs, configuration | `file://config.json`, `db://schema`, API docs |
| **Prompts** | User (explicit trigger) | Workflow templates, analysis recipes | `code_review`, `summarize_data`, `debug_error` |

**Decision guide:**
- Does it *do* something or *change* state? -> **Tool**
- Does it *provide* context the model should see? -> **Resource**
- Is it a *reusable workflow* a user triggers? -> **Prompt**

---

## Intent-First Design

### The 25-Tool Performance Cliff

Agent performance degrades significantly beyond 25 tools. Research shows:
- **10-15 tools**: Optimal agent decision accuracy
- **16-25 tools**: Acceptable with clear, distinct descriptions
- **26-30 tools**: Noticeable degradation in tool selection accuracy
- **31+ tools**: Severe decision paralysis — agents pick wrong tools or fail to act

### The 3-Step Rule

If accomplishing a single user intent requires more than 3 sequential tool calls, the tool design is too granular. Consolidate related operations into higher-level intent-based tools.

### 7 MCP Anti-Patterns

| Anti-Pattern | What Happens | Fix |
|---|---|---|
| **Tool Explosion** | One tool per API endpoint (50+ tools) | Consolidate by user intent |
| **Atomic Obsession** | Every field is a separate tool call | Bundle related operations |
| **Developer-First Descriptions** | "Executes POST /api/v1/users" | "Create a new user account with name and email" |
| **Missing Examples** | No usage examples in descriptions | Every tool needs `input_example`, `output_example`, and `common_mistakes` in its description — LLMs need examples 10× more than humans do |
| **Auto-Generation Without Curation** | OpenAPI -> tools without review | Curate: merge, rename, add context |
| **REST Trap** | CRUD maps 1:1 to tools | Design around user workflows, not endpoints |
| **Context Window Neglect** | Tools return 50KB JSON blobs | Paginate, summarize, progressive disclosure |

### Agent Stories Framework

Design tools by mapping user intent:

1. **Map intent**: "As an agent, I need to ___"
2. **Consolidate by intent**: Group API calls that serve one intent into one tool
3. **Write agent-directive responses**: Every response tells the agent what to do next

### When to Split vs Combine Tools

Split a tool into multiple when:
- **Safety Boundary**: Read vs write operations need different authorization. Keep `delete_user_safe` (marks inactive, recoverable) separate from `delete_user_permanent` (GDPR erasure, irreversible). A hallucinated `permanent: true` flag with a consolidated tool destroys data — split these.
- **Context Boundary**: Tool would need >5 unrelated parameters
- **Logic Boundary**: Handler exceeds ~200 lines or has completely different error paths
- **Output Format Boundary**: Keep `get_summary` (100 tokens, quick reference) separate from `get_full_detail` (2,000 tokens, complete history). Consolidating with a `detail_level` parameter forces the agent to reason about context budget — keep different output scales as separate tools.
- **Execution Context Boundary**: Keep `execute_sync` (blocks, waits for result) separate from `execute_async` (returns job ID, requires polling). The agent's next action fundamentally differs depending on the execution pattern — these are not the same intent even if they trigger the same operation.
- **Execution Time Variance Boundary**: If a tool sometimes completes in 200ms and sometimes takes 30 seconds (depending on input), consolidation breaks timeout handling — callers cannot set a sensible timeout. Split into a `fast_path` variant and a `slow_path` / async variant with different timeout contracts.

**The rule:** If the agent's decision tree genuinely branches on a dimension (safety, format, blocking model), that dimension deserves a separate tool. If it's just a parameter variant of the same intent, consolidate. Over-consolidation is its own anti-pattern.

### 11 Server Patterns — Priority Order

You do not need to build all 11. Build in this order based on agent value vs effort:

**Build First — covers 70% of agent needs:**
1. **Authentication Server** — `authenticate()`, `refresh_token()`, `verify_permissions()`. Every other server depends on this.
2. **Data Query Server** — `search_records()`, `fetch_by_id()`, `get_related_data()`. 80% of API usage is reads.
3. **State Management Server** — `create_resource()`, `update_resource()`, `transition_state()`. All "make changes" intents.

**Build Second:**
4. **Diagnostic Server** — `check_api_health()`, `get_rate_limit_status()`
5. **Error Investigation Server** — `explain_error()`, `trace_request()`

**Build Third (when specific needs arise):**
6. **Batch Operations Server** — long-running async jobs
7. **Schema Discovery Server** — self-documenting behavior for dynamic agents
8. **Testing Sandbox Server** — safe experimentation without real side effects

**Build Last (only if needed):**
9. **Event & Notification Server**
10. **Configuration Server**
11. **Cost & Budget Server** — only mandatory at ~$1M+/month agent spend

Most production systems need servers 1–5. The rest are additions based on specific domain requirements.

### Schema Flattening Rule

MCP tool input/output schemas MUST NOT nest beyond 2 levels deep. Older models without structured output support struggle with deeper nesting, and even current models make more parameter extraction errors with deep schemas.

```typescript
// ❌ WRONG — 3 levels deep
inputSchema: {
  filter: z.object({
    location: z.object({
      city: z.string(),    // ← 3rd level
    })
  })
}

// ✅ CORRECT — max 2 levels
inputSchema: {
  filter_location_city: z.string().optional(),
  filter_min_rating: z.number().optional(),
}
```

**When you must represent nested data in responses:** flatten with dot-notation keys (`filter.location.city`) or include a `flat_*` alias at the top level alongside the nested version.

### The "3 AM Test"

Two distinct checks — both must pass before shipping:

**Design-time (tool clarity):** Can an on-call engineer tell from the tool name and description what it does, without reading the code? If not, rename or add clarity.

**Production-time (escalation trigger):** Would you want to be paged at 3 AM for this tool's failure mode? If yes, add human-in-the-loop using the standard escalation payload. Auto-escalate when:
- Financial impact exceeds $10k per operation
- Operation is irreversible (delete data, cancel enterprise contracts)
- Legal or compliance implications
- Agent confidence is below 70% on a critical decision

```json
{
  "requires_human": true,
  "severity": "critical",
  "reason": "Financial impact exceeds $10k threshold",
  "action_attempted": "Refund $15,000 to customer",
  "estimated_impact": "$15k immediate, $50k ARR at risk",
  "escalation_sla_minutes": 15,
  "suggested_actions": ["Verify customer identity", "Check fraud signals"]
}
```

This payload is the standard structure for `escalate_to_human` in high-stakes contexts. The `escalation_sla_minutes` field sets the response time expectation; `estimated_impact` gives the human operator context to triage urgency.

---
