# Node/TypeScript MCP Server -- Advanced Features and Complete Example

## Complete Example

```typescript
#!/usr/bin/env node
/**
 * MCP Server for Example Service.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import Fastify from "fastify";
import { z } from "zod";
import axios, { AxiosError } from "axios";

// Constants
const API_BASE_URL = "https://api.example.com/v1";
const CHARACTER_LIMIT = 25000;

enum ResponseFormat {
  MARKDOWN = "markdown",
  JSON = "json"
}

// Zod schemas
const UserSearchInputSchema = z.object({
  query: z.string().min(2).max(200).describe("Search string to match against names/emails"),
  limit: z.number().int().min(1).max(100).default(20).describe("Maximum results to return"),
  offset: z.number().int().min(0).default(0).describe("Number of results to skip"),
  response_format: z.nativeEnum(ResponseFormat).default(ResponseFormat.MARKDOWN)
    .describe("Output format")
}).strict();

type UserSearchInput = z.infer<typeof UserSearchInputSchema>;

// Shared utilities
async function makeApiRequest<T>(
  endpoint: string, method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
  data?: any, params?: any
): Promise<T> {
  const response = await axios({
    method, url: `${API_BASE_URL}/${endpoint}`, data, params,
    timeout: 30000,
    headers: { "Content-Type": "application/json", "Accept": "application/json" }
  });
  return response.data;
}

function handleApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.response) {
      switch (error.response.status) {
        case 404: return "Error: Resource not found.";
        case 403: return "Error: Permission denied.";
        case 429: return "Error: Rate limit exceeded.";
        default: return `Error: API request failed with status ${error.response.status}`;
      }
    } else if (error.code === "ECONNABORTED") {
      return "Error: Request timed out.";
    }
  }
  return `Error: ${error instanceof Error ? error.message : String(error)}`;
}

// Create server
const server = new McpServer({ name: "example-mcp", version: "1.0.0" });

// Register tools
server.registerTool(
  "example_search_users",
  {
    title: "Search Example Users",
    description: `Search for users by name, email, or team. Returns paginated results.`,
    inputSchema: UserSearchInputSchema,
    annotations: {
      readOnlyHint: true, destructiveHint: false,
      idempotentHint: true, openWorldHint: true
    }
  },
  async (params: UserSearchInput) => {
    try {
      const data = await makeApiRequest<any>("users/search", "GET", undefined, {
        q: params.query, limit: params.limit, offset: params.offset
      });
      const users = data.users || [];
      if (!users.length) {
        return { content: [{ type: "text", text: `No users found matching '${params.query}'` }] };
      }
      const output = {
        total: data.total, count: users.length, offset: params.offset,
        users: users.map((u: any) => ({
          id: u.id, name: u.name, email: u.email,
          ...(u.team ? { team: u.team } : {}), active: u.active ?? true
        })),
        has_more: data.total > params.offset + users.length
      };
      const textContent = JSON.stringify(output, null, 2);
      return {
        content: [{ type: "text", text: textContent }],
        structuredContent: output
      };
    } catch (error) {
      return { content: [{ type: "text", text: handleApiError(error) }] };
    }
  }
);

// Transport selection
async function runStdio() {
  if (!process.env.EXAMPLE_API_KEY) {
    console.error("ERROR: EXAMPLE_API_KEY environment variable is required");
    process.exit(1);
  }
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("MCP server running via stdio");
}

async function runHTTP() {
  if (!process.env.EXAMPLE_API_KEY) {
    console.error("ERROR: EXAMPLE_API_KEY environment variable is required");
    process.exit(1);
  }
  const app = Fastify({ logger: true });
  app.addContentTypeParser('application/json', { parseAs: 'string' }, (req, body, done) => {
    try { done(null, JSON.parse(body as string)); } catch (e) { done(e as Error); }
  });
  app.post('/mcp', async (req, reply) => {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined, enableJsonResponse: true
    });
    reply.raw.on('close', () => transport.close());
    await server.connect(transport);
    await transport.handleRequest(req.raw, reply.raw, req.body);
  });
  const port = parseInt(process.env.PORT || '3000');
  await app.listen({ port, host: '0.0.0.0' });
  console.error(`MCP server running on http://localhost:${port}/mcp`);
}

const transport = process.env.TRANSPORT || 'stdio';
if (transport === 'http') {
  runHTTP().catch(e => { console.error("Server error:", e); process.exit(1); });
} else {
  runStdio().catch(e => { console.error("Server error:", e); process.exit(1); });
}
```

---

## Advanced MCP Features

### Resource Registration

Expose data as resources for efficient, URI-based access:

```typescript
import { ResourceTemplate } from "@modelcontextprotocol/sdk/types.js";

server.registerResource(
  {
    uri: "file://documents/{name}",
    name: "Document Resource",
    description: "Access documents by name",
    mimeType: "text/plain"
  },
  async (uri: string) => {
    const match = uri.match(/^file:\/\/documents\/(.+)$/);
    if (!match) throw new Error("Invalid URI format");
    const content = await loadDocument(match[1]);
    return { contents: [{ uri, mimeType: "text/plain", text: content }] };
  }
);

server.registerResourceList(async () => {
  const documents = await getAvailableDocuments();
  return {
    resources: documents.map(doc => ({
      uri: `file://documents/${doc.name}`,
      name: doc.name,
      mimeType: "text/plain",
      description: doc.description
    }))
  };
});
```

**When to use Resources vs Tools:**
- **Resources**: Data access with simple URI-based parameters, relatively static data
- **Tools**: Complex operations requiring validation, business logic, or side effects

### Transport Options

#### Streamable HTTP (Recommended for Remote Servers)

```typescript
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import Fastify from "fastify";

const app = Fastify({ logger: true });
app.post('/mcp', async (req, reply) => {
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined, enableJsonResponse: true
  });
  reply.raw.on('close', () => transport.close());
  await server.connect(transport);
  await transport.handleRequest(req.raw, reply.raw, req.body);
});
await app.listen({ port: 3000 });
```

#### stdio (For Local Integrations)

```typescript
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
const transport = new StdioServerTransport();
await server.connect(transport);
```

**Transport selection:**
- **Streamable HTTP**: Web services, remote access, multiple clients
- **stdio**: Command-line tools, local development, subprocess integration

### Notification Support

```typescript
server.notification({ method: "notifications/tools/list_changed" });
server.notification({ method: "notifications/resources/list_changed" });
```

Use notifications sparingly -- only when server capabilities genuinely change.

### Prompt Registration

Expose reusable prompt templates for common workflows:

```typescript
server.registerPrompt(
  "analyze_data",
  {
    title: "Data Analysis",
    description: "Generate a structured analysis of the provided dataset",
    argsSchema: {
      dataset: z.string().describe("Dataset name or URI"),
      analysisType: z.enum(["summary", "anomaly", "trend", "comparison"]),
      timeRange: z.string().optional().describe("Time range (e.g., '7d', '30d', '1y')"),
    },
  },
  async ({ dataset, analysisType, timeRange }) => ({
    messages: [{
      role: "user",
      content: {
        type: "text",
        text: `Analyze the dataset "${dataset}" with ${analysisType} analysis${timeRange ? ` for the last ${timeRange}` : ''}.\n\nProvide:\n1. Key findings\n2. Statistical summary\n3. Recommendations\n4. Confidence level for each finding`,
      },
    }],
  })
);
```

**When to use Prompts vs Tools:**
- **Prompts**: Reusable templates for common analysis/review workflows (user-triggered)
- **Tools**: Operations with side effects, complex validation, or API calls (model-invoked)
- **Resources**: Read-only data access via URI (app-controlled)

### Streaming Progress

For long-running operations, emit progress updates via streamable HTTP transport (SSE transport is deprecated in favor of streamable HTTP):

```typescript
interface StreamingToolResponse {
  type: 'progress' | 'partial' | 'complete' | 'error';
  progress?: number;        // 0-100
  partialData?: unknown;
  finalData?: unknown;
  error?: string;
}

// Example: Tool with progress streaming
server.registerTool(
  "bulk_export_data",
  {
    title: "Bulk Data Export",
    description: "Export large datasets with progress updates",
    inputSchema: {
      query: z.string(),
      format: z.enum(["json", "csv", "parquet"]),
      chunkSize: z.number().default(1000),
    },
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true }
  },
  async ({ query, format, chunkSize }) => {
    const totalRecords = await dataService.count(query);
    let processed = 0;

    for await (const chunk of dataService.streamQuery(query, chunkSize)) {
      processed += chunk.length;
      // Progress is tracked internally; final result includes summary
    }

    return {
      content: [{ type: "text", text: JSON.stringify({
        success: true,
        data: { totalRecords: processed, format },
        next_actions: ["download_export", "verify_data_integrity", "schedule_recurring_export"],
        suggestion: `Export complete with ${processed} records. Download or verify data integrity.`,
      })}]
    };
  }
);
```

---

## Quality Checklist

### Strategic Design
- [ ] Tools enable complete workflows, not just API endpoint wrappers
- [ ] Tool names reflect natural task subdivisions
- [ ] Response formats optimize for agent context efficiency
- [ ] Error messages guide agents toward correct usage

### Implementation Quality
- [ ] All tools registered using `registerTool` with complete configuration
- [ ] All tools include `title`, `description`, `inputSchema`, and `annotations`
- [ ] Annotations correctly set (readOnlyHint, destructiveHint, idempotentHint, openWorldHint)
- [ ] All Zod schemas have proper constraints and `.strict()` enforcement
- [ ] Descriptions include return value examples and complete schema documentation

### TypeScript Quality
- [ ] Strict TypeScript enabled in tsconfig.json
- [ ] No use of `any` type -- use `unknown` or proper types
- [ ] All async functions have explicit `Promise<T>` return types
- [ ] Error handling uses proper type guards

### Advanced Features (where applicable)
- [ ] Resources registered for appropriate data endpoints
- [ ] Prompts registered for reusable workflow templates
- [ ] Appropriate transport configured (stdio or streamable HTTP)
- [ ] Streaming progress for long-running operations
- [ ] Notifications implemented for dynamic server capabilities

### Production Readiness (where applicable)
- [ ] Agent-directive responses with `next_actions` and `suggestion` in every tool
- [ ] Error taxonomy with `MCPErrorCode` and recovery actions
- [ ] Resilience stack (circuit breaker, rate limiter, retry) for external API calls
- [ ] Input sanitization and attack pattern detection
- [ ] Audit logging with correlation IDs
- [ ] Kubernetes health probes (liveness/readiness)
- [ ] Graceful shutdown handling (SIGTERM/SIGINT)
- [ ] `escalate_to_human` tool for life-safety/fraud/high-value operations
- [ ] ≤25 intent-based tools (no endpoint-mapped CRUD explosion)

### Project Configuration
- [ ] Package.json includes all necessary dependencies
- [ ] Build script produces working JavaScript in dist/
- [ ] Main entry point configured as dist/index.js
- [ ] Server name follows format: `{service}-mcp-server`

### Code Quality
- [ ] Pagination properly implemented where applicable
- [ ] Large responses check CHARACTER_LIMIT and truncate with clear messages
- [ ] Common functionality extracted into reusable functions
- [ ] `npm run build` completes successfully without errors
