---
description: Angular-specific XSS vulnerability scanner. Detects unsafe innerHTML, bypassSecurityTrust* misuse, template injection, DomSanitizer bypasses, and missing sanitization. Produces framework-aware findings with DOMPurify fix patterns.
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
---

# Angular XSS Vulnerability Scan

Target path: `$ARGUMENTS` (default: `src/`).

## Step 1: Scan for dangerous patterns

Run grep searches for each severity category against `*.ts` and `*.html` files in the target path.

### CRITICAL

```bash
# Script injection bypass
grep -rnE 'bypassSecurityTrustScript\(' $ARGUMENTS --include='*.ts'
# URL injection bypass (may enable javascript: URIs)
grep -rnE 'bypassSecurityTrustUrl\(' $ARGUMENTS --include='*.ts'
```

### HIGH

```bash
# HTML injection bypass
grep -rnE 'bypassSecurityTrustHtml\(' $ARGUMENTS --include='*.ts'
# Direct DOM manipulation bypassing Angular sanitizer
grep -rnE 'ElementRef.*nativeElement.*innerHTML' $ARGUMENTS --include='*.ts'
# Direct innerHTML assignment in component code
grep -rnE 'document\..*\.innerHTML\s*=' $ARGUMENTS --include='*.ts'
# Template innerHTML binding
grep -rnE '\[innerHTML\]=' $ARGUMENTS --include='*.html'
```

### MEDIUM

```bash
# nativeElement innerHTML in any context
grep -rnE 'nativeElement\.innerHTML' $ARGUMENTS --include='*.ts'
# bypassSecurityTrustResourceUrl (less severe but still risky)
grep -rnE 'bypassSecurityTrustResourceUrl\(' $ARGUMENTS --include='*.ts'
```

## Step 2: Report each finding

For every match, output in this format:

```
SEVERITY: [CRITICAL/HIGH/MEDIUM]
File: [path:line]
Pattern: [the detected code snippet]
Risk: XSS via unsanitized user input reaching DOM
Fix: [specific Angular-idiomatic fix from the table below]
```

### Secure alternatives

| Vulnerable Pattern | Fix |
|--------------------|-----|
| `bypassSecurityTrustHtml(val)` | Call `DomSanitizer.sanitize(SecurityContext.HTML, val)` first, then bypass only if needed |
| `[innerHTML]="var"` | Use `[textContent]="var"` for plain text; for HTML, pipe through `DomSanitizer` |
| `nativeElement.innerHTML = x` | Use `Renderer2.setProperty(el, 'innerHTML', sanitized)` instead |
| `bypassSecurityTrustScript(x)` | Remove entirely -- load scripts via Angular-approved methods only |
| `bypassSecurityTrustUrl(x)` | Validate URL scheme is `http:`/`https:` before bypass; reject `javascript:` |
| Any HTML rendering | Add `DOMPurify.sanitize(input)` as secondary defense before rendering |

## Step 3: Prevention checklist

Print after findings:

```
ANGULAR XSS PREVENTION CHECKLIST:
[ ] Template bindings: No [innerHTML] with unsanitized user data
[ ] TypeScript: No nativeElement.innerHTML assignments
[ ] Sanitizer: bypassSecurityTrust* called only after DomSanitizer.sanitize()
[ ] CSP: Content-Security-Policy header prevents inline scripts
[ ] DOMPurify: Installed and applied before any HTML rendering
[ ] No user data in template string interpolation that renders HTML tags
```

## Risk Score

Calculate: `(CRITICAL count x 10) + (HIGH count x 7) + (MEDIUM count x 4)`, capped at 100.

```
XSS RISK SCORE: [score]/100
Remediation priority: [CRITICAL findings first, then HIGH, then MEDIUM]
Total findings: [N] (CRITICAL: [n], HIGH: [n], MEDIUM: [n])
```

$ARGUMENTS
