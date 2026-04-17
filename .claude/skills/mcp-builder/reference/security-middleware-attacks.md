## Security Middleware Integration

### Pre-Tool-Execution Hook

```typescript
import { SecurityManager, DEFAULT_SECURITY_CONFIG } from './security-manager.js';

export class SecureMCPServer {
  private securityManager: SecurityManager;

  constructor() {
    this.securityManager = new SecurityManager(DEFAULT_SECURITY_CONFIG);
  }

  /**
   * Middleware to sanitize and validate all tool arguments
   */
  private async securityMiddleware(toolName: string, args: any): Promise<any> {
    try {
      // Validate and sanitize all arguments
      const sanitizedArgs = this.securityManager.validateInput(args);

      // Log security event (audit trail)
      console.log('[SECURITY] Tool execution:', {
        tool: toolName,
        timestamp: new Date().toISOString(),
        sanitized: JSON.stringify(sanitizedArgs) !== JSON.stringify(args),
      });

      return sanitizedArgs;
    } catch (error) {
      // Log security violation
      console.error('[SECURITY VIOLATION]', {
        tool: toolName,
        error: error.message,
        args: JSON.stringify(args).substring(0, 200), // Log first 200 chars
        timestamp: new Date().toISOString(),
      });

      throw new Error(`Security validation failed: ${error.message}`);
    }
  }

  /**
   * Wrap tool handler with security checks
   */
  registerSecureTool(name: string, handler: (args: any) => Promise<any>) {
    return async (args: any) => {
      // Pre-execution: sanitize and validate
      const sanitizedArgs = await this.securityMiddleware(name, args);

      // Execute tool with sanitized arguments
      const result = await handler(sanitizedArgs);

      // Post-execution: sanitize output (if needed)
      return this.securityManager.sanitizeInput(result);
    };
  }
}
```

### Prompt Injection Detection

MCP tools receive inputs that ultimately come from LLM agents. A malicious payload in the tool's input could attempt to redirect the agent's behavior by embedding instruction overrides. Always scan string inputs for known prompt injection signatures before processing.

**Required patterns to detect:**

```typescript
const PROMPT_INJECTION_PATTERNS: RegExp[] = [
  // Classic override attempts
  /ignore\s+(previous|all|above|prior)\s+(instructions?|prompts?|context)/i,
  /disregard\s+(previous|all|above|prior)\s+(instructions?|prompts?|context)/i,
  /forget\s+(everything|all|previous|prior)/i,

  // Role-play jailbreaks
  /you\s+are\s+now\s+(a|an)\s+/i,
  /pretend\s+(you\s+are|to\s+be)/i,
  /act\s+as\s+(if\s+you\s+are|a|an)\s+/i,

  // Common LLM delimiters used in multi-turn injection
  /\[INST\]/i,       // Llama/Mistral instruction delimiter
  /<<SYS>>/i,        // Llama system prompt delimiter
  /<\|im_start\|>/i, // Chatml format
  /<\|system\|>/i,   // Phi/Falcon system token

  // Tool/function call injection
  /\{\s*"tool"\s*:/i,
  /\{\s*"function"\s*:/i,
];

export function detectPromptInjection(input: string): boolean {
  return PROMPT_INJECTION_PATTERNS.some((pattern) => pattern.test(input));
}
```

**Where to call it:** Run `detectPromptInjection()` on every string input field before schema validation passes the value to business logic. Return `INVALID_INPUT` error with `recovery_action: "remove_injection_attempt"` — do NOT process the request.

**Log every detection:** Emit a structured security event (`attack_pattern_detected`, type `prompt_injection`) with the input hash (not the raw input) so security teams can monitor for campaigns.

---

### Brute Force Detection

MCP HTTP servers must detect and block repeated failed authentication attempts from the same IP. Without this, API keys can be brute-forced even with timing-safe comparison.

```typescript
interface BruteForceConfig {
  maxFailedAttempts: number;  // attempts before block (default: 5)
  windowMs: number;           // rolling window (default: 5 minutes)
  blockDurationMs: number;    // how long to block (default: 15 minutes)
}

export const DEFAULT_BRUTE_FORCE_CONFIG: BruteForceConfig = {
  maxFailedAttempts: 5,
  windowMs: 5 * 60 * 1000,      // 5 minutes
  blockDurationMs: 15 * 60 * 1000, // 15 minutes
};

export class SecurityMonitor {
  // key: IP address → { attempts: timestamp[], blockedUntil?: number }
  private readonly ipState = new Map<string, { attempts: number[]; blockedUntil?: number }>();

  recordFailedAuth(ip: string): void {
    const now = Date.now();
    let state = this.ipState.get(ip) ?? { attempts: [] };

    // Prune attempts outside the rolling window
    state.attempts = state.attempts.filter(
      (ts) => now - ts < this.config.windowMs,
    );
    state.attempts.push(now);

    if (state.attempts.length >= this.config.maxFailedAttempts) {
      state.blockedUntil = now + this.config.blockDurationMs;
      // Emit security event for SIEM/alerting
    }

    this.ipState.set(ip, state);
  }

  isBlocked(ip: string): boolean {
    const state = this.ipState.get(ip);
    if (!state?.blockedUntil) return false;
    if (Date.now() > state.blockedUntil) {
      // Block expired — clear state
      this.ipState.delete(ip);
      return false;
    }
    return true;
  }

  constructor(private readonly config: BruteForceConfig = DEFAULT_BRUTE_FORCE_CONFIG) {}
}
```

**Integration in auth middleware:**

```typescript
// In your Fastify preHandler / Express middleware
const ip = request.ip;

if (securityMonitor.isBlocked(ip)) {
  reply.status(429).header('Retry-After', '900').send({
    error: 'TOO_MANY_REQUESTS',
    message: 'Too many failed authentication attempts. Try again later.',
  });
  return;
}

const isValid = validateApiKey(providedKey, validKeys);
if (!isValid) {
  securityMonitor.recordFailedAuth(ip);
  reply.status(401).send({ error: 'UNAUTHORIZED' });
  return;
}
```

**Memory management:** Periodically prune expired entries to prevent unbounded Map growth in high-traffic deployments. A simple `setInterval` every 5 minutes that removes entries where `blockedUntil < now` and `attempts.length === 0` is sufficient.

---

### SSRF Protection (Server-Side Request Forgery)

MCP servers that make outbound HTTP calls to upstream services (matching engines, APIs, databases) MUST block requests to cloud metadata endpoints and internal hostnames. Without this, a malicious agent could craft tool inputs that redirect outbound calls to `169.254.169.254` and exfiltrate cloud credentials.

**Required blocked destinations:**

```typescript
const BLOCKED_HOSTNAMES = new Set([
  '169.254.169.254',          // AWS/GCP/Azure IMDS
  'metadata.google.internal', // GCP metadata server
  'metadata.internal',        // GCP alias
  '100.100.100.200',          // Alibaba Cloud metadata
  '192.0.0.1',                // Azure metadata alias
]);

const BLOCKED_IP_PREFIXES = [
  '127.',     // loopback
  '10.',      // RFC 1918 private
  '172.16.',  // RFC 1918 private
  '192.168.', // RFC 1918 private
  '169.254.', // link-local (IMDS range)
  '::1',      // IPv6 loopback
  'fc00:',    // IPv6 private
];

/**
 * Validate every upstream URL at server startup and before each outbound call.
 * Throw at startup if config points at a blocked host — never silently allow.
 */
export function assertSafeUpstreamUrl(rawUrl: string): void {
  let parsed: URL;
  try {
    parsed = new URL(rawUrl);
  } catch {
    throw new Error(`SSRF guard: invalid URL format: ${rawUrl}`);
  }

  const hostname = parsed.hostname.toLowerCase();

  if (BLOCKED_HOSTNAMES.has(hostname)) {
    throw new Error(`SSRF guard: blocked hostname: ${hostname}`);
  }

  for (const prefix of BLOCKED_IP_PREFIXES) {
    if (hostname.startsWith(prefix)) {
      throw new Error(`SSRF guard: blocked IP range: ${hostname}`);
    }
  }
}
```

**When to call `assertSafeUpstreamUrl`:**
1. **At startup** — call it on every upstream URL from config (matching_engine URL, external API URLs). If any are blocked, the server crashes immediately with a clear message. This is the fail-fast rule applied to SSRF.
2. **Before dynamic outbound calls** — if tool inputs can influence which URL is called, validate the resolved URL before the request.

**In config loading:**

```typescript
// config.ts — called inside loadConfig() after parsing env vars
assertSafeUpstreamUrl(config.matchingEngineUrl);
assertSafeUpstreamUrl(config.externalApiUrl);
// Add every outbound URL your server calls
```

> **PropertyHarbor note:** `config.ts:290-310` implements `assertSafeUpstreamUrl()` with the exact blocked set above. It is called at the end of `loadConfig()` so any misconfigured upstream URL crashes the server before it accepts connections.

