### HTTP Response Headers

```typescript
import Fastify from 'fastify';
import { SecurityManager, DEFAULT_SECURITY_CONFIG } from './security-manager.js';

const app = Fastify({ logger: true });
const securityManager = new SecurityManager(DEFAULT_SECURITY_CONFIG);

// Apply security headers to all responses
app.addHook('onSend', async (request, reply) => {
  const headers = securityManager.getSecurityHeaders();
  for (const [key, value] of Object.entries(headers)) {
    reply.header(key, value);
  }
});
```

### Complete Integration Example

```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { SecurityManager, DEFAULT_SECURITY_CONFIG } from './security-manager.js';
import { z } from 'zod';

export class ProductionMCPServer {
  private server: McpServer;
  private securityManager: SecurityManager;

  constructor() {
    this.server = new McpServer({ name: 'secure-mcp-server', version: '1.0.0' });
    this.securityManager = new SecurityManager(DEFAULT_SECURITY_CONFIG);
    this.setupSecureTools();
  }

  /**
   * Wrap a tool handler with security validation and sanitization
   */
  private secureHandler<T>(handler: (args: T) => Promise<any>) {
    return async (args: T) => {
      // Security layer: validate and sanitize
      const sanitizedArgs = this.securityManager.validateInput(args);

      // Execute tool with sanitized arguments
      const result = await handler(sanitizedArgs);

      // Sanitize output
      const sanitizedResult = this.securityManager.sanitizeInput(result);

      return {
        content: [
          {
            type: 'text' as const,
            text: JSON.stringify(sanitizedResult),
          },
        ],
      };
    };
  }

  private setupSecureTools() {
    this.server.registerTool(
      'example_tool',
      {
        title: 'Example Secure Tool',
        description: 'Example secure tool with input sanitization',
        inputSchema: {
          query: z.string().describe('Search query'),
        },
        annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      },
      this.secureHandler(async ({ query }) => {
        // Tool implementation here
        return { status: 'success', query };
      })
    );
  }

  async start() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}
```

## PII Tokenization — Keeping Sensitive Data Out of LLM Context

**Problem:** When MCP tools return data containing PII (email addresses, SSNs, phone numbers), that data enters the LLM's context window. This creates two problems: (1) compliance risk — LLMs are not SOC2/GDPR-compliant PII stores; (2) token waste — PII fields are verbose and consume context budget that should be used for reasoning.

**Solution:** Tokenize PII fields server-side before returning data. The LLM works with opaque tokens. The server maintains the token-to-value mapping and substitutes tokens back when performing actual operations (email sends, database writes).

This is distinct from stripping PII from logs (covered in compliance flags above). Tokenization allows the LLM to *reference* PII records without ever *seeing* the raw values.

```typescript
import { randomUUID } from 'crypto';

interface TokenMap {
  [token: string]: string;  // token → real value
}

export class PiiTokenizer {
  private tokenStore = new Map<string, TokenMap>();  // sessionId → token map

  tokenize(
    data: Record<string, unknown>[],
    sensitiveFields: string[],
    sessionId: string
  ): { tokenized: Record<string, unknown>[]; sessionId: string } {
    const tokenMap: TokenMap = this.tokenStore.get(sessionId) ?? {};

    const tokenized = data.map(record => {
      const safe: Record<string, unknown> = { ...record };
      for (const field of sensitiveFields) {
        if (safe[field] !== undefined) {
          const token = `TOK_${randomUUID().replace(/-/g, '').slice(0, 8).toUpperCase()}`;
          tokenMap[token] = String(safe[field]);
          safe[field] = token;
        }
      }
      return safe;
    });

    this.tokenStore.set(sessionId, tokenMap);
    return { tokenized, sessionId };
  }

  detokenize(value: string, sessionId: string): string {
    const tokenMap = this.tokenStore.get(sessionId) ?? {};
    return tokenMap[value] ?? value;  // unknown token → pass through
  }

  // Call in tool handler when the agent passes a token back for an action
  resolveTokens(
    params: Record<string, unknown>,
    sessionId: string
  ): Record<string, unknown> {
    const tokenMap = this.tokenStore.get(sessionId) ?? {};
    return Object.fromEntries(
      Object.entries(params).map(([k, v]) => [
        k,
        typeof v === 'string' && tokenMap[v] ? tokenMap[v] : v,
      ])
    );
  }
}
```

### Usage in Tool Handler

```typescript
const tokenizer = new PiiTokenizer();
const PII_FIELDS = ['email', 'phone', 'ssn', 'address', 'full_name'];

// Tool: list_users — returns tokenized PII to LLM
server.registerTool('list_users', { ... }, async ({ filter }, extra) => {
  const sessionId = extra.sessionId ?? 'default';
  const users = await db.query('SELECT * FROM users WHERE status = $1', [filter]);

  const { tokenized } = tokenizer.tokenize(users, PII_FIELDS, sessionId);

  return {
    content: [{ type: 'text', text: JSON.stringify({ users: tokenized }) }]
  };
});

// Tool: send_email — agent passes token back; server resolves before sending
server.registerTool('send_email', { ... }, async ({ recipient_token, subject, body }, extra) => {
  const sessionId = extra.sessionId ?? 'default';
  const realEmail = tokenizer.detokenize(recipient_token, sessionId);

  await emailService.send({ to: realEmail, subject, body });
  return { content: [{ type: 'text', text: 'Email sent.' }] };
});
```

### When to Use

| Scenario | Use Tokenization? |
|---|---|
| Tool returns user records with email/phone/SSN | ✅ Yes — LLM should not see raw PII |
| Tool returns anonymized aggregate stats | ❌ No — no PII present |
| Tool receives a user reference to perform an action | ✅ Yes — resolve token server-side before acting |
| Internal server-to-server call (no LLM in path) | ❌ No — tokenization is for LLM context protection |

**Token lifespan:** Tokens are session-scoped. When the MCP session ends, clear the token store for that session. Do NOT persist tokens to disk — if the token store leaks, the mapping becomes a PII breach.

**Dual benefit:** Beyond compliance, tokenization reduces context consumption. A token (`TOK_A1B2C3D4`) is ~6 tokens. A real email address (`alice.johnson@company.com`) is ~10-15 tokens. At scale across hundreds of records, this difference is meaningful.

---

## Recommended Dependencies

```json
{
  "dependencies": {
    "dompurify": "~3.2.0",
    "jsdom": "~25.0.0"
  },
  "devDependencies": {
    "@types/dompurify": "~3.2.0",
    "@types/jsdom": "~21.1.0"
  }
}
```

## Installation

```bash
npm install dompurify jsdom
npm install --save-dev @types/dompurify @types/jsdom
```

## Testing Security Patterns

```typescript
import { describe, it, expect } from 'vitest';
import { SecurityManager, DEFAULT_SECURITY_CONFIG } from './security-manager.js';

describe('SecurityManager', () => {
  const manager = new SecurityManager(DEFAULT_SECURITY_CONFIG);

  it('should detect SQL injection patterns', () => {
    expect(manager.containsAttackPatterns("SELECT * FROM users WHERE id=1")).toBe(true);
    expect(manager.containsAttackPatterns("admin' OR '1'='1")).toBe(true);
    expect(manager.containsAttackPatterns("'; DROP TABLE users--")).toBe(true);
  });

  it('should detect XSS patterns', () => {
    expect(manager.containsAttackPatterns("<script>alert('xss')</script>")).toBe(true);
    expect(manager.containsAttackPatterns("javascript:alert(1)")).toBe(true);
    expect(manager.containsAttackPatterns("<img onerror='alert(1)'>")).toBe(true);
  });

  it('should detect path traversal patterns', () => {
    expect(manager.containsAttackPatterns("../../etc/passwd")).toBe(true);
    expect(manager.containsAttackPatterns("%2e%2e%2f")).toBe(true);
  });

  it('should detect command injection patterns', () => {
    expect(manager.containsAttackPatterns("file.txt; rm -rf /")).toBe(true);
    expect(manager.containsAttackPatterns("$(whoami)")).toBe(true);
    expect(manager.containsAttackPatterns("file.txt | bash -c 'cat /etc/passwd'")).toBe(true);
  });

  it('should not flag legitimate text as command injection', () => {
    expect(manager.containsAttackPatterns("Q&A session")).toBe(false);
    expect(manager.containsAttackPatterns("C++ (advanced)")).toBe(false);
    expect(manager.containsAttackPatterns("Price: $100")).toBe(false);
  });

  it('should sanitize HTML from strings', () => {
    const input = "<script>alert('test')</script>Hello";
    const sanitized = manager.sanitizeInput(input);
    expect(sanitized).not.toContain('<script>');
    expect(sanitized).toContain('Hello');
  });

  it('should recursively sanitize objects', () => {
    const input = {
      name: "<b>John</b>",
      nested: {
        value: "<script>alert(1)</script>",
      },
    };
    const sanitized = manager.sanitizeInput(input);
    expect(sanitized.name).toBe('John');
    expect(sanitized.nested.value).not.toContain('<script>');
  });

  it('should throw on input exceeding max length', () => {
    const longInput = 'a'.repeat(20000);
    expect(() => manager.sanitizeInput(longInput)).toThrow('exceeds maximum length');
  });
});
```

## CI/CD Security Pipeline

Every MCP server CI pipeline MUST include these security scanning steps before merge:

```yaml
# .github/workflows/security.yml
name: Security Gate
on: [pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # 1. Static analysis — catches injection, prototype pollution, unsafe eval
      - name: CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          languages: javascript

      # 2. Dependency vulnerabilities — blocks on HIGH or CRITICAL CVEs
      - name: npm audit
        run: npm audit --audit-level=high

      # 3. Secret detection — catches API keys, tokens, private keys committed to repo
      - name: Gitleaks secret scan
        uses: gitleaks/gitleaks-action@v2

      # 4. Container scanning — if you build a Docker image
      - name: Trivy container scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.IMAGE_NAME }}
          severity: HIGH,CRITICAL
          exit-code: 1

      # 5. License compliance — blocks GPL dependencies in proprietary code
      - name: License check
        run: npx license-checker --onlyAllow "MIT;Apache-2.0;BSD-2-Clause;BSD-3-Clause;ISC"
```

**Minimum gates (all must pass before merge):**
- CodeQL: zero new HIGH/CRITICAL findings
- npm audit: zero HIGH/CRITICAL CVEs in production dependencies
- Gitleaks: zero secrets detected
- Trivy: zero HIGH/CRITICAL container vulnerabilities (if containerized)

## Security Checklist

- [ ] Enable all security detection patterns
- [ ] Set appropriate `maxInputLength` for your use case
- [ ] Apply security headers to all HTTP responses
- [ ] Log all security violations to audit trail
- [ ] Sanitize both inputs and outputs
- [ ] Test with known attack patterns
- [ ] Rate-limit tool calls (not shown here, use library like `express-rate-limit`)
- [ ] Implement authentication/authorization before security layer
- [ ] Monitor logs for repeated security violations
- [ ] Keep dependencies updated (DOMPurify only needed if responses contain user-generated HTML content; for JSON-RPC, Zod/Pydantic schema validation is the primary defense)
- [ ] **SSRF protection** — call `assertSafeUpstreamUrl()` on every configured upstream URL at startup; block IMDS ranges (169.254.x.x), cloud metadata hostnames, and RFC 1918 private ranges
- [ ] **No dynamic URL construction from tool inputs** — if tool args influence outbound URLs, validate the fully-resolved URL through `assertSafeUpstreamUrl()` before the request
- [ ] **Prompt injection detection** — scan all string inputs for override patterns (`ignore previous instructions`, `[INST]`, `<<SYS>>`, `<|im_start|>`) before processing; return INVALID_INPUT and log with input hash
- [ ] **Brute force detection** — track failed auth attempts per IP with rolling window (5 attempts / 5 min); block IP for 15 min with 429 + Retry-After header; prune expired entries periodically
- [ ] **CI/CD security pipeline** — CodeQL + npm audit + Gitleaks + Trivy + license check on every PR; all must pass before merge
- [ ] **PII tokenization** — if tools return records with PII fields (email, phone, SSN, address), tokenize before returning to LLM; maintain session-scoped token store server-side; resolve tokens when agent passes them back for write operations
- [ ] **Code execution tool sandboxing** — if your MCP server implements a code execution tool: use `bubblewrap` (Linux) or `seatbelt` (macOS) for process isolation; scope credentials in the sandbox narrowly (read-only where possible); never pass long-lived admin credentials into the sandbox
