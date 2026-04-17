# Node/TypeScript MCP Server -- Setup and Configuration

## Overview

Node/TypeScript-specific setup for MCP servers using the MCP TypeScript SDK. Covers project structure, package configuration, server initialization, naming conventions, and build/run workflow.

---

## Quick Reference

### Key Imports
```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import Fastify from "fastify";
import { z } from "zod";
import { Pool } from "undici";
import pino from "pino";
```

### Server Initialization
```typescript
const server = new McpServer({
  name: "service-mcp-server",
  version: "1.0.0"
});
```

### Tool Registration Pattern
```typescript
server.registerTool(
  "tool_name",
  {
    title: "Tool Display Name",
    description: "What the tool does",
    inputSchema: { param: z.string() },
    outputSchema: { result: z.string() }
  },
  async ({ param }) => {
    const output = { result: `Processed: ${param}` };
    return {
      content: [{ type: "text", text: JSON.stringify(output) }],
      structuredContent: output
    };
  }
);
```

---

## MCP TypeScript SDK

The official MCP TypeScript SDK provides:
- `McpServer` class for server initialization
- `registerTool` method for tool registration
- Zod schema integration for runtime input validation
- Type-safe tool handler implementations

**IMPORTANT - Use Modern APIs Only:**
- **DO use**: `server.registerTool()`, `server.registerResource()`, `server.registerPrompt()`
- **DO NOT use**: Old deprecated APIs such as `server.tool()`, `server.setRequestHandler(ListToolsRequestSchema, ...)`, or manual handler registration
- The `register*` methods provide better type safety, automatic schema handling, and are the recommended approach

## Server Naming Convention

Node/TypeScript MCP servers must follow this naming pattern:
- **Format**: `{service}-mcp-server` (lowercase with hyphens)
- **Examples**: `github-mcp-server`, `jira-mcp-server`, `stripe-mcp-server`

The name should be:
- General (not tied to specific features)
- Descriptive of the service/API being integrated
- Easy to infer from the task description
- Without version numbers or dates

## Project Structure

```
{service}-mcp-server/
├── package.json
├── tsconfig.json
├── README.md
├── src/
│   ├── index.ts          # Main entry point with McpServer initialization
│   ├── types.ts          # TypeScript type definitions and interfaces
│   ├── tools/            # Tool implementations (one file per domain)
│   ├── services/         # API clients and shared utilities
│   ├── schemas/          # Zod validation schemas
│   └── constants.ts      # Shared constants (API_URL, CHARACTER_LIMIT, etc.)
└── dist/                 # Built JavaScript files (entry point: dist/index.js)
```

### Production Structure (3-Layer Architecture)

For production MCP servers, use a 3-layer architecture that separates transport, protocol, and business logic:

```
{service}-mcp-server/
├── src/
│   ├── transport/              # Layer 1: Transport
│   │   ├── stdio.ts            # stdio transport for local AI assistants
│   │   ├── http.ts             # HTTP streamable transport (production)
│   │   ├── session.ts          # Session management with UUID
│   │   └── health.ts           # Health check endpoints
│   ├── protocol/               # Layer 2: Protocol
│   │   ├── mcp-server.ts       # McpServer configuration + registration
│   │   ├── tool-registry.ts    # Centralized tool definitions
│   │   ├── resource-registry.ts # Resource management
│   │   ├── prompt-registry.ts  # Prompt management
│   │   └── schemas/            # Zod schemas for all tools
│   ├── business/               # Layer 3: Business Logic
│   │   ├── services/           # Core business services
│   │   ├── clients/            # External API clients (undici)
│   │   ├── cache/              # Caching layer
│   │   └── transformers/       # Data transformers
│   ├── config/                 # Zod-validated config loader
│   ├── errors/                 # Error taxonomy (MCPErrorCode)
│   ├── types/                  # TypeScript types + branded types
│   └── utils/                  # Logger (pino), correlation IDs
├── docker/
│   └── Dockerfile              # Multi-stage production build
├── package.json
├── tsconfig.json
└── vitest.config.ts
```

See [production-deployment.md](production-deployment.md) for the full production structure with auth, security, observability, and K8s support.

## Package Configuration

### package.json

Version numbers below reflect the latest at time of writing. Always check npm for the current version before starting a new project.

```json
{
  "name": "{service}-mcp-server",
  "version": "1.0.0",
  "description": "MCP server for {Service} API integration",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "start": "node dist/index.js",
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "clean": "rm -rf dist"
  },
  "engines": {
    "node": ">=18"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "~1.17.5", // Check latest: https://www.npmjs.com/package/@modelcontextprotocol/sdk
    "zod": "~3.25.76",
    "undici": "~7.16.0",
    "pino": "~9.9.4"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "tsx": "^4.19.2",
    "typescript": "~5.9.2",
    "vitest": "~3.2.4"
  }
}
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2024",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2024"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "allowSyntheticDefaultImports": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

## Building and Running

Always build TypeScript code before running:

```bash
# Build the project
npm run build

# Run the server
npm start

# Development with auto-reload
npm run dev
```

Always ensure `npm run build` completes successfully before considering the implementation complete.
