# Semgrep Custom Rules

Project-specific Semgrep rules covering the full tech stack: Java/Spring Boot, TypeScript/NestJS/Angular,
Python/FastAPI, and cross-language patterns. These rules target vulnerabilities specific to our codebase
and supplement the built-in Semgrep rulesets.

## Rule File

Save this as `.semgrep.yml` in your project root.
Run: `semgrep --config=.semgrep.yml .`

```yaml
rules:
  # ----------------------------
  # Java / Spring Boot Rules
  # ----------------------------
  - id: spring-sql-injection
    patterns:
      - pattern: $JDBC.query("..." + $VAR, ...)
      - pattern: $JDBC.execute("..." + $VAR)
    message: "Potential SQL injection: string concatenation in JDBC query. Use parameterized queries."
    severity: ERROR
    languages: [java]
    metadata:
      cwe: CWE-89
      owasp: A03:2021

  - id: spring-hardcoded-secret
    pattern: |
      @Value("${...}:$SECRET_LITERAL")
    message: "Hardcoded secret as @Value fallback. Use environment variables without defaults for secrets."
    severity: WARNING
    languages: [java]
    metadata:
      cwe: CWE-798

  - id: spring-unsafe-redirect
    pattern: |
      $RESPONSE.sendRedirect($REQUEST.getParameter(...))
    message: "Unsafe redirect using user-controlled input. Validate redirect target against allowlist."
    severity: ERROR
    languages: [java]
    metadata:
      cwe: CWE-601

  # ----------------------------
  # TypeScript / NestJS / Angular Rules
  # ----------------------------
  - id: ts-dangerous-inner-html
    patterns:
      - pattern: $ELEM.innerHTML = $VAR
    message: "Dangerous innerHTML assignment. Use DOMPurify.sanitize() or Angular DomSanitizer first."
    severity: ERROR
    languages: [typescript, javascript]
    metadata:
      cwe: CWE-79

  - id: nestjs-missing-body-decorator
    pattern: |
      @Post(...)
      async $METHOD($PARAM: $TYPE) { ... }
    message: "POST handler parameter may be missing @Body() DTO decorator with validation."
    severity: WARNING
    languages: [typescript]
    metadata:
      cwe: CWE-20

  - id: ts-hardcoded-aws-key
    pattern: |
      $VAR = "AKIA..."
    message: "Hardcoded AWS access key detected. Use IAM roles or environment variables."
    severity: ERROR
    languages: [typescript, javascript]
    metadata:
      cwe: CWE-798

  # ----------------------------
  # Python / FastAPI Rules
  # ----------------------------
  - id: python-sql-format-string
    patterns:
      - pattern: $CURSOR.execute("..." % $VAR)
      - pattern: $CURSOR.execute(f"...{$VAR}...")
    message: "SQL injection via string formatting. Use parameterized queries: cursor.execute(query, (param,))"
    severity: ERROR
    languages: [python]
    metadata:
      cwe: CWE-89

  - id: python-path-traversal
    patterns:
      - pattern: open($PATH + $USER_INPUT, ...)
      - pattern: open(f"...{$USER_INPUT}...", ...)
    message: "Path traversal: user input in file path. Use pathlib and validate against allowed base directory."
    severity: ERROR
    languages: [python]
    metadata:
      cwe: CWE-22

  - id: python-command-injection
    patterns:
      - pattern: subprocess.call(..., shell=True)
      - pattern: subprocess.run(..., shell=True)
      - pattern: os.system($VAR)
    message: "Command injection risk with shell=True or os.system. Use subprocess with list args instead."
    severity: ERROR
    languages: [python]
    metadata:
      cwe: CWE-78

  # ----------------------------
  # Cross-Language Rules
  # ----------------------------
  - id: hardcoded-jwt-secret
    patterns:
      - pattern: SECRET_KEY = "..."
      - pattern: JWT_SECRET = "..."
      - pattern: secret = "..."
    message: "Hardcoded JWT/session secret. Load from environment variable at runtime."
    severity: ERROR
    languages: [python, typescript, javascript, java]
    metadata:
      cwe: CWE-798
```

## Usage

Run the custom rules against your project:

```bash
semgrep --config=.semgrep.yml .
```

Combine with built-in rulesets for broader coverage:

```bash
semgrep --config=.semgrep.yml --config=p/security-audit --config=p/owasp-top-ten .
```

## Adding Custom Rules

Each rule follows this structure:

```yaml
- id: unique-rule-id          # Descriptive, kebab-case identifier
  pattern: <semgrep pattern>   # Or patterns/pattern-either for multiple matches
  message: "What is wrong and how to fix it."
  severity: ERROR|WARNING|INFO
  languages: [python, java]    # Target languages
  metadata:
    cwe: CWE-NNN              # CWE identifier
    owasp: ANN:YYYY            # OWASP category (optional)
```

Use `patterns` (list) when you need to match multiple conditions (AND logic).
Use `pattern-either` when any one pattern should trigger the rule (OR logic).

## Suppressing False Positives

Add an inline comment to suppress a specific rule on a line:

```python
secret = os.environ["SECRET"]  # nosemgrep: hardcoded-jwt-secret
```

```java
String key = System.getenv("KEY"); // nosemgrep: spring-hardcoded-secret
```

```typescript
const token = process.env.TOKEN; // nosemgrep: ts-hardcoded-aws-key
```

The format is always `# nosemgrep: rule-id` (or `// nosemgrep: rule-id` for C-style comments).
