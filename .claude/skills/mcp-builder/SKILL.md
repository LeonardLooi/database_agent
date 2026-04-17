---
name: mcp-builder
description: Use when building, testing, or designing MCP (Model Context Protocol) servers to
  integrate external APIs and services. Covers tool design, schema validation, error handling,
  security, resilience patterns, and production evaluations for Python (FastMCP) and
  Node/TypeScript (MCP SDK) implementations.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch
metadata:
  triggers: MCP server, Model Context Protocol, MCP integration, FastMCP, MCP tool, MCP resource, build MCP
  related-skills: agentic-ai-dev, python-dev
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

## Iron Law

Never publish an MCP server without testing all tool schemas against the MCP spec; always validate tool descriptions are >= 10 words and parameters are fully typed.

# MCP Server Development Guide

Create MCP servers that enable LLMs to interact with external services through well-designed tools.

## High-Level Workflow

### Phase 1: Research and Plan

- Study MCP spec from `https://modelcontextprotocol.io/sitemap.xml` (append `.md` for markdown)
- Fetch TypeScript SDK README from `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`
- Fetch Python SDK README from `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- Load design principles, agent patterns, and error taxonomy from reference files (see table below)

### Phase 2: Implement

- Set up project structure using language-specific reference files (see table below)
- Create shared utilities: API client, error handling, response formatting, pagination
- For each tool: define input schema (Zod/Pydantic), output schema, description, annotations, and async implementation
- **Recommended stack**: TypeScript with streamable HTTP (remote) or stdio (local)

### Phase 3: Review and Test

- Review for: no duplication, consistent error handling, full type coverage, clear tool descriptions
- TypeScript: `npm run build` then test with `npx @modelcontextprotocol/inspector`
- Python: `python -m py_compile your_server.py` then test with MCP Inspector

### Phase 4: Create Evaluations

- Create 10 complex, realistic evaluation questions requiring multiple tool calls
- Each question must be: independent, read-only, complex, realistic, verifiable, stable
- Output as XML with `<evaluation>` root containing `<qa_pair>` elements

## Tool Implementation Checklist

For each tool, define:
- **Input schema** — Zod (TypeScript) or Pydantic (Python) with constraints and descriptions
- **Output schema** — Use `outputSchema` and `structuredContent` where possible
- **Description** — Concise summary, parameter docs, return type
- **Annotations** — `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- **Implementation** — Async/await, proper error handling, pagination support
- **Agent directive** — Include `next_actions` and `suggestion` in every response
- **Error taxonomy** — Use `MCPErrorCode` enum with recovery actions

## Reference Files

| Resource | When to Load |
|----------|-------------|
| [MCP Design Principles](reference/mcp-design-principles.md) | Phase 1 — intent-first design, tool count limits, naming, anti-patterns |
| [MCP Design Server Patterns](reference/mcp-design-server-patterns.md) | Phase 1/2 — naming, response formats, pagination, transport, 3-layer architecture |
| [MCP Design Context Efficiency](reference/mcp-design-context-efficiency.md) | Phase 2 — tool description budget (180-token template), context efficiency, filesystem discovery |
| [MCP Quality Standards](reference/mcp-quality-standards.md) | Phase 1 — security, annotations, testing, audit logging, MCP primitives |
| [MCP Quality Compliance](reference/mcp-quality-compliance.md) | Phase 2 — SOC2/GDPR/PCI compliance flags, canonical scorer delegation |
| [MCP Quality Versioning](reference/mcp-quality-versioning.md) | Phase 2 — tool versioning, breaking changes, canary rollouts |
| [Agent Design Patterns — Core](reference/agent-design-patterns.md) | Phase 1 — patterns 1-5: directive, confidence, error, disclosure, linking |
| [Agent Design Patterns — Advanced](reference/agent-design-patterns-advanced.md) | Phase 2 — patterns 6-10: idempotency, context carryover, circuit breaker, audit trail |
| [Agent Design Patterns — Domain](reference/agent-design-patterns-domain.md) | Phase 2 — domain presets (payment, healthcare, e-commerce), tool consolidation |
| [Error Taxonomy](reference/error-taxonomy.md) | Phase 1 — error codes, recovery hints, no-fake-empty-data |
| [Branded Types & Audit](reference/error-branded-types-audit.md) | Phase 2 — type-safe IDs, Zod integration, audit logging |
| [TypeScript Setup](reference/node-mcp-setup.md) | Phase 2 — project structure, package config, build |
| [TypeScript Patterns](reference/node-mcp-patterns.md) | Phase 2 — tool naming, Zod schemas, tool structure |
| [TypeScript Patterns Advanced](reference/node-mcp-patterns-advanced.md) | Phase 2 — response formats, pagination, error handling, utilities |
| [TypeScript Advanced](reference/node-mcp-advanced.md) | Phase 2 — complete example, resources, transport |
| [Python Setup](reference/python-mcp-setup.md) | Phase 2 — Python SDK, tool structure, Pydantic |
| [Python Patterns](reference/python-mcp-patterns.md) | Phase 2 — pagination, errors, complete example |
| [Python Advanced](reference/python-mcp-advanced.md) | Phase 2 — context, resources, lifespan, quality |
| [Resilience Core](reference/resilience-core.md) | Phase 2 — circuit breaker, bulkhead, rate limiter, retry strategy |
| [Resilience Caching & Pool](reference/resilience-retry-cache.md) | Phase 2 — rate limiter, retry, LRU caching |
| [Resilience Production](reference/resilience-production.md) | Phase 2 — connection pool, composing patterns, loop detection |
| [Security Core](reference/security-core.md) | Phase 2 — SecurityManager, attack patterns (SQL/XSS/path traversal/command injection) |
| [Security Middleware & Attacks](reference/security-middleware-attacks.md) | Phase 2 — middleware integration, prompt injection, brute force, SSRF |
| [Security PII & Compliance](reference/security-pii-compliance.md) | Phase 2 — PII tokenization, testing, CI/CD pipeline, security checklist |
| [Observability Tracing](reference/observability-tracing.md) | Phase 2 — OpenTelemetry setup, custom MCP spans, 6-metric pyramid |
| [Observability Metrics](reference/observability-metrics.md) | Phase 2 — metrics collection, sampling strategies |
| [Observability Monitoring](reference/observability-monitoring.md) | Phase 2 — integration example, post-deployment health targets, alert tiers, cost reduction |
| [Production Runtime — Shutdown & Health](reference/production-runtime-shutdown-health.md) | Phase 2 — graceful shutdown, K8s health checks |
| [Production Runtime — Multi-Tenant](reference/production-runtime-multi-tenant.md) | Phase 2 — AsyncLocalStorage context, quotas, audit |
| [Production Infrastructure Docker](reference/production-deployment-docker.md) | Phase 2 — Docker multi-stage build, docker-compose, Kubernetes manifests |
| [Production Infrastructure Structure](reference/production-deployment-structure.md) | Phase 2 — 3-layer folder structure, layer responsibilities |
| [Evaluation Criteria](reference/evaluation-criteria.md) | Phase 4 — question/answer design |
| [Evaluation Running](reference/evaluation-running.md) | Phase 4 — CLI, setup, troubleshooting |

## Common Mistakes

- **Scoring/ranking logic in MCP layer** — MCP tools are API entry points only. All business logic (scoring, filtering, matching) belongs in an upstream service. See [reference/mcp-quality-compliance.md](reference/mcp-quality-compliance.md).
- **Exceeding 25 tools** — Agent decision accuracy degrades sharply past 25 tools. Consolidate by user intent, not by API endpoint. See [reference/mcp-design-principles.md](reference/mcp-design-principles.md).
- **Missing `next_actions` in responses** — Every tool response must include `next_actions` (machine-readable) and `suggestion` (human-readable) or agents stall. No exceptions.
- **Returning empty list/null on error** — Never return `[]` or `null` as a silent fallback. Return a structured `MCPErrorCode` error so the agent knows what failed and how to recover.
- **Tool descriptions written for developers** — "Executes POST /api/v1/vendors" tells an LLM nothing. Write for the agent: "USE WHEN: Finding service vendors for a property. EXAMPLES: ..."

## Error Handling

> For the full error taxonomy and circuit breaker patterns, Read [reference/error-taxonomy.md](reference/error-taxonomy.md)

**Server startup failures**: Validate all required environment variables at startup. Fail fast with a clear error message — never silently fall back to defaults.

**Tool execution errors**: Return structured MCP error responses with error codes. Never let unhandled exceptions crash the server.

```typescript
// ✅ Required pattern — structured error, never silent failure
server.registerTool('search_vendors', { ... }, async (args) => {
  try {
    const results = await upstreamClient.search(args);
    return {
      content: [{ type: 'text', text: JSON.stringify({
        data: results,
        next_actions: ['vendor_get_details', 'vendor_request_quote'],
        suggestion: `Found ${results.length} vendors. Call vendor_get_details for full profiles.`,
      })}]
    };
  } catch (error) {
    return {
      isError: true,
      content: [{ type: 'text', text: JSON.stringify({
        code: 'SERVICE_UNAVAILABLE',
        message: error.message,
        retry_after_ms: 5000,
        recovery_actions: ['retry_search', 'use_cached_results'],
        fallback_tool: 'search_vendors_cached',
      })}]
    };
  }
});
```

## Verify

Before publishing any MCP server:

- [ ] `npm run build` exits 0 (TypeScript) or `python -m py_compile server.py` exits 0 (Python)
- [ ] `npx @modelcontextprotocol/inspector <entrypoint>` — all tools listed with correct schemas
- [ ] All tool descriptions are ≥ 10 words
- [ ] All input parameters are fully typed (no `any` in TypeScript, no untyped `dict` in Python)
- [ ] Every tool response includes `next_actions` and `suggestion` fields
- [ ] `npm test` (or `uv run pytest`) exits 0 with coverage thresholds met
- [ ] No unhandled exceptions — all errors return structured `MCPErrorCode` responses
- [ ] Security checklist in [reference/security-core.md](reference/security-core.md) reviewed
