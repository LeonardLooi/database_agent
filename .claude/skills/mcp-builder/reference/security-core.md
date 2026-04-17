# Security Architecture for Production MCP Servers

## Security Layers Diagram

```
External Request
    ↓
Security Headers
    ↓
Input Sanitization (Schema Validation)
    ↓
Attack Pattern Detection
    ↓
Threat Monitoring
    ↓
Audit Logging
    ↓
Business Logic
```

## Security Manager Implementation

### SecurityConfig Interface

```typescript
export interface SecurityConfig {
  sanitizationEnabled: boolean;
  attackDetectionEnabled: boolean;
  sqlInjectionDetection: boolean;
  xssDetection: boolean;
  pathTraversalDetection: boolean;
  commandInjectionDetection: boolean;
  maxInputLength: number;
}
```

### SecurityManager Class

```typescript
import { JSDOM } from 'jsdom';
import DOMPurify from 'dompurify';

export class SecurityManager {
  private config: SecurityConfig;
  private domPurify: DOMPurify.DOMPurifyI;

  constructor(config: SecurityConfig) {
    this.config = config;

    // Initialize DOMPurify with jsdom for server-side sanitization
    const window = new JSDOM('').window;
    this.domPurify = DOMPurify(window as unknown as Window);
  }

  /**
   * Recursively sanitize input data (strings, arrays, objects)
   */
  sanitizeInput(input: any): any {
    if (!this.config.sanitizationEnabled) {
      return input;
    }

    if (typeof input === 'string') {
      // Check max length
      if (this.config.maxInputLength > 0 && input.length > this.config.maxInputLength) {
        throw new Error(`Input exceeds maximum length of ${this.config.maxInputLength}`);
      }

      // Sanitize HTML content
      return this.domPurify.sanitize(input, {
        ALLOWED_TAGS: [], // Strip all HTML tags by default
        ALLOWED_ATTR: [],
        KEEP_CONTENT: true, // Keep text content
      });
    }

    if (Array.isArray(input)) {
      return input.map(item => this.sanitizeInput(item));
    }

    if (input !== null && typeof input === 'object') {
      const sanitized: Record<string, any> = {};
      for (const [key, value] of Object.entries(input)) {
        const sanitizedKey = this.sanitizeInput(key);
        sanitized[sanitizedKey] = this.sanitizeInput(value);
      }
      return sanitized;
    }

    return input;
  }

  /**
   * Detect common attack patterns in input strings
   */
  containsAttackPatterns(input: string): boolean {
    if (!this.config.attackDetectionEnabled) {
      return false;
    }

    const patterns = [
      // SQL Injection patterns
      ...(this.config.sqlInjectionDetection ? [
        /(\bSELECT\b.*\bFROM\b)/i,
        /(\bINSERT\b.*\bINTO\b)/i,
        /(\bUPDATE\b.*\bSET\b)/i,
        /(\bDELETE\b.*\bFROM\b)/i,
        /(\bUNION\b.*\bALL\b)/i,
        /(\bUNION\b.*\bSELECT\b)/i,
        /(\bOR\b\s+['"]*\d+\s*=\s*\d+)/i,
        /(\bAND\b\s+['"]*\d+\s*=\s*\d+)/i,
        /(--\s*$)/,
        /(;\s*DROP\b.*\bTABLE\b)/i,
        /('OR'.*'=')/i,
        /(\bEXEC\b|\bEXECUTE\b)/i,
      ] : []),

      // XSS patterns
      ...(this.config.xssDetection ? [
        /<script[^>]*>.*?<\/script>/gi,
        /javascript:/gi,
        /on\w+\s*=\s*["'][^"']*["']/gi, // onerror=, onclick=, etc.
        /<iframe/gi,
        /<object/gi,
        /<embed/gi,
        /eval\s*\(/gi,
        /expression\s*\(/gi,
      ] : []),

      // Path Traversal patterns
      ...(this.config.pathTraversalDetection ? [
        /\.\.\//g,
        /\.\.\\/g,
        /%2e%2e%2f/gi,
        /%2e%2e%5c/gi,
        /\/etc\/passwd/i,
        /\/etc\/shadow/i,
        /c:\\windows/i,
      ] : []),

      // Command Injection patterns (context-aware to reduce false positives on "Q&A", "$100", etc.)
      ...(this.config.commandInjectionDetection ? [
        /;\s*(rm|cat|ls|wget|curl|bash|sh|python|node)\b/i,
        /\|\s*(bash|sh|nc|netcat)\b/i,
        /`[^`]+`/,
        /\$\([^)]+\)/,
        /\$\{[^}]+\}/,
        /&&\s*(rm|cat|ls|wget|curl|bash|sh|python|node)\b/i,
        /\|\|\s*(rm|cat|ls|wget|curl|bash|sh|python|node)\b/i,
      ] : []),
    ];

    return patterns.some(pattern => pattern.test(input));
  }

  /**
   * Validate and sanitize input, throw if attack patterns detected
   */
  validateInput(input: any): any {
    // First check for attack patterns (before sanitization to catch attempts)
    if (typeof input === 'string' && this.containsAttackPatterns(input)) {
      throw new Error('Potential attack pattern detected in input');
    }

    // Then sanitize
    return this.sanitizeInput(input);
  }

  /**
   * Get security headers for HTTP responses
   */
  getSecurityHeaders(): Record<string, string> {
    return {
      // Prevent XSS attacks
      'Content-Security-Policy': [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self'",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
      ].join('; '),

      // Prevent MIME type sniffing
      'X-Content-Type-Options': 'nosniff',

      // Prevent clickjacking
      'X-Frame-Options': 'DENY',

      // Enable browser XSS protection
      'X-XSS-Protection': '1; mode=block',

      // Enforce HTTPS
      'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',

      // Control referrer information
      'Referrer-Policy': 'strict-origin-when-cross-origin',

      // Control browser features
      'Permissions-Policy': [
        'geolocation=()',
        'microphone=()',
        'camera=()',
        'payment=()',
        'usb=()',
      ].join(', '),
    };
  }
}
```

### Default Security Configuration

```typescript
export const DEFAULT_SECURITY_CONFIG: SecurityConfig = {
  sanitizationEnabled: true,
  attackDetectionEnabled: true,
  sqlInjectionDetection: true,
  xssDetection: true,
  pathTraversalDetection: true,
  commandInjectionDetection: true,
  maxInputLength: 10000, // 10KB
};
```
