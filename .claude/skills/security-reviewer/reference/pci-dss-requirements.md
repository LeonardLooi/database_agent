# PCI DSS Requirements Reference

Use when building or reviewing any feature that handles payment card data, processes payments,
or integrates with payment processors (Stripe, PayPal, Square).

---

## PCI DSS Compliance Levels

| Level | Criteria | Annual Requirement |
|-------|----------|--------------------|
| **Level 1** | > 6 million card transactions/year | Report on Compliance (ROC) by Qualified Security Assessor |
| **Level 2** | 1–6 million transactions/year | Self-Assessment Questionnaire (SAQ) + quarterly scans |
| **Level 3** | 20,000–1 million e-commerce transactions/year | SAQ + quarterly scans |
| **Level 4** | < 20,000 e-commerce or < 1 million total/year | SAQ + quarterly scans (recommended) |

**Practical implication for most apps:** Use hosted payment pages (Stripe Checkout, PayPal) to achieve
SAQ-A (fewest requirements, ~20 questions). Handling card data directly escalates to SAQ-D (~300 questions).

---

## The 12 PCI DSS Core Requirements

### Goal 1: Build and Maintain a Secure Network
**Req 1 — Firewall configuration**
- Install and maintain a firewall between the internet and cardholder data environment (CDE)
- Deny all traffic not explicitly required
- Document all firewall rules with business justification

**Req 2 — No vendor defaults**
- Change all vendor-supplied default passwords before deploying any system component
- Remove or disable unnecessary default accounts
- Disable unnecessary services, protocols, and ports

### Goal 2: Protect Cardholder Data
**Req 3 — Protect stored cardholder data**
- See "Data Minimization" section below — never store prohibited data
- Encrypt Primary Account Numbers (PAN) wherever stored
- Mask PAN when displayed (show only last 4 digits max in UI)
- Destroy cardholder data when no longer needed

**Req 4 — Encrypt transmission**
- Use TLS 1.2+ for all transmission of cardholder data over public networks
- Never send unencrypted PANs via email, chat, or messaging
- Disable SSL, early TLS, and weak cipher suites

### Goal 3: Maintain a Vulnerability Management Program
**Req 5 — Anti-malware**
- Deploy anti-virus/anti-malware on all systems commonly affected by malware
- Keep anti-malware current and perform periodic scans

**Req 6 — Secure systems and applications**
- Protect all system components from known vulnerabilities via security patches
- Apply critical patches within 1 month of release
- Follow secure development practices (OWASP, input validation, output encoding)
- Separate development/test environments from production — test data must never include real PANs

### Goal 4: Implement Strong Access Control
**Req 7 — Restrict access by business need-to-know**
- Grant access to cardholder data only to those whose job requires it
- Default-deny: all access denied unless explicitly granted

**Req 8 — Identify and authenticate all users**
- Assign unique IDs to every user — no shared accounts for CDE access
- Implement MFA for all access to the CDE
- Passwords: minimum 7 characters, mix of numeric and alphabetic, changed every 90 days
- Lock accounts after maximum 6 failed attempts

**Req 9 — Restrict physical access**
- Restrict physical access to systems that store, process, or transmit cardholder data
- Log all physical access; review logs at least quarterly
- Destroy physical media containing cardholder data securely

### Goal 5: Monitor and Test Networks
**Req 10 — Track and monitor all access**
- Log all access to network resources and cardholder data
- Log entries must include: user ID, event type, date/time, success/failure, data accessed
- Retain logs for at least 1 year; 3 months immediately available
- Review logs daily for anomalies

**Req 11 — Regularly test security**
- Run internal and external vulnerability scans quarterly (ASV-approved for external)
- Perform penetration testing at least annually and after major changes
- Deploy intrusion detection/prevention systems (IDS/IPS)

### Goal 6: Maintain an Information Security Policy
**Req 12 — Security policy**
- Maintain a security policy addressing all PCI DSS requirements
- Conduct annual risk assessment
- Implement security awareness training for all personnel
- Maintain an incident response plan — test annually

---

## Data Minimization — What You Can and Cannot Store

### NEVER Store (Prohibited — even if encrypted)
| Data | Description |
|------|-------------|
| Full magnetic stripe data | Track 1 and Track 2 data from card swipe |
| CVV / CVV2 / CVC / CID | 3-4 digit security code on card |
| PIN / PIN block | Personal identification number |

Storing any of the above is a **critical PCI violation** regardless of encryption.

### MAY Store (if encrypted and access-controlled)
| Data | Notes |
|------|-------|
| PAN (Primary Account Number) | Must be encrypted at rest; masked in UI (last 4 only) |
| Cardholder name | Low risk; still access-control |
| Expiration date | Low risk; still access-control |
| Service code | Low risk |

### Recommended: Store Nothing — Use Tokens
Use payment processor tokens (Stripe `customer_id` + `payment_method_id`) instead of any card data.
Your database stores only the processor's reference ID. Zero card data = zero PCI storage scope.

```
// What your DB should store
{
  stripe_customer_id: "cus_xxx",      // ✅ Token — safe to store
  stripe_payment_method_id: "pm_xxx", // ✅ Token — safe to store
}

// What your DB must NEVER store
{
  card_number: "4242424242424242",  // ❌ PAN — never
  cvv: "123",                       // ❌ PROHIBITED — never
  full_track: "...",                // ❌ PROHIBITED — never
}
```

---

## SAQ Types (Self-Assessment Questionnaire)

| SAQ | Who It Applies To | Questions | Scope |
|-----|------------------|-----------|-------|
| **SAQ A** | E-commerce using fully hosted payment page (Stripe Checkout, PayPal). No card data on your systems. | ~20 | Lowest — aim for this |
| **SAQ A-EP** | E-commerce with JavaScript-based payment form embedded in your page (Stripe Elements, PayPal SDK). Card data handled in provider iframe but your page loads it. | ~180 | Medium |
| **SAQ B** | Imprint-only or standalone dial-out terminals; no electronic cardholder data storage | ~40 | Low |
| **SAQ C** | Payment application systems connected to internet; no electronic cardholder data storage | ~80 | Medium |
| **SAQ D** | Any merchant storing, processing, or transmitting cardholder data not covered above | ~300 | Highest — avoid this |

**Workspace recommendation:** Build with SAQ A in mind. Use Stripe Checkout (hosted) or Stripe Elements
(embedded iframe) — both keep card data out of your systems and qualify for SAQ A or SAQ A-EP.

---

## PCI Scope Reduction Strategies

1. **Use hosted payment pages** (Stripe Checkout, PayPal Hosted Fields) — achieves SAQ A
2. **Tokenize immediately** — use processor tokens, never store card data
3. **Network segmentation** — isolate any systems that touch card data from the rest of your infrastructure
4. **Outsource** — use fully PCI-compliant processors; you inherit their compliance for card handling
5. **No storage** — never cache, log, or persist card numbers, even temporarily

---

## Webhook Security Requirements (PCI-relevant)

| Requirement | Why It Matters |
|-------------|---------------|
| **Verify webhook signatures** | Unverified webhooks can trigger fraudulent payment state changes |
| **Use raw body for verification** | JSON middleware modifies the body and breaks HMAC signature validation |
| **Idempotent handlers** | Providers retry on failure — processing twice can double-charge or double-fulfill |
| **Respond in < 200ms** | Return `2xx` before any DB writes; slow responses trigger retries |
| **Re-fetch from provider API** | Never trust the webhook payload alone — verify payment status via API call |

---

## Audit Logging Requirements (Req 10)

Every access to cardholder data or payment operations MUST produce an audit log entry containing:

- User ID (who)
- Action taken (what)
- Timestamp in UTC (when)
- Resource accessed (which)
- Success or failure (outcome)
- Source IP address

```
// Minimum audit log entry structure
{
  "timestamp": "2026-03-15T10:23:41Z",
  "user_id": "usr_abc123",
  "action": "view_payment_method",
  "resource": "payment_methods/pm_xxx",
  "result": "success",
  "ip": "203.0.113.42"
}
```

Log payment events that require mandatory audit entries (per `security-review-checklist.md`):
- Payment initiated, succeeded, failed
- Refund created
- Subscription created, modified, cancelled
- Payment method added or removed
- Any admin access to payment records

---

## Common PCI Violations (Red Flags in Code Review)

| Violation | Severity | What to Look For |
|-----------|----------|-----------------|
| Logging card numbers | CRITICAL | `log.info(cardNumber)`, `console.log(req.body)` on payment endpoints |
| Storing CVV in DB | CRITICAL | Any `cvv`, `cvc`, `security_code` column in payment-related tables |
| Unverified webhooks | CRITICAL | Missing signature verification before processing payment events |
| HTTP (not HTTPS) for card data | CRITICAL | Any non-TLS transmission path for payment data |
| Hardcoded API keys | HIGH | `stripe.api_key = "sk_live_..."` in source code |
| No access control on payment endpoints | HIGH | Missing `@UseGuards(JwtAuthGuard)` on payment routes |
| Test cards accepted in production | HIGH | Misconfigured gateway accepting `4242 4242 4242 4242` on live site |
| Full PAN in error messages | HIGH | Stack traces or error responses containing card numbers |
| Shared DB user for CDE | MEDIUM | Same DB credentials for payment tables and general app tables |
| No log rotation / retention | MEDIUM | Logs not retained for 1 year |

---

## Load When

- Implementing any payment processing feature
- Reviewing code that touches payment data, webhooks, or billing
- Designing database schemas that include payment-related tables
- Preparing for a security audit of payment flows
- Choosing between hosted vs custom payment UI (SAQ scope decision)
