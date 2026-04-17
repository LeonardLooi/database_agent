# Agent Guardrails Checklist

> Scope: AI/Agent-specific security controls — guardrail pipeline design, prompt injection defense, output validation, audit logging for agents. For application-layer checks see `security-review-checklist.md`. For infrastructure see `owasp-infrastructure-baseline.md`.

---

## 12-Layer Pipeline Reference

Grounded in `weather-agent/backend/src/guardrails/guardrail_manager.py` and `models.py`.

### Execution Order

```
Input path:  L1 → L2 → L3 → L4 → L5 → [L9, L10] (async, parallel)
Output path: L6 → L7 → L8 → [L9, L10, L12] (async, parallel)
```

L11 (Encryption) is invoked on-demand, not in the sequential check path.

### Layer Definitions

| Layer | Name | Validates | Blocking? | Severity when triggered |
|-------|------|-----------|-----------|------------------------|
| L1 | INPUT_VALIDATION | Type, length (`max_input_length=10000`), format | YES | HIGH/CRITICAL |
| L2 | PII_DETECTION | SSN, credit card, phone, email, address, DOB, passport, bank account, IP | YES (with redaction) | HIGH |
| L3 | AUTH_AUTHZ | Role-based access, session validity | YES | CRITICAL |
| L4 | PROMPT_INJECTION | Instruction override attempts, jailbreak patterns | YES | CRITICAL |
| L5 | CONTENT_FILTERING | Hate speech, violence, self-harm, dangerous advice, profanity, misinformation | YES | HIGH/CRITICAL |
| L6 | HALLUCINATION_DETECTION | Response grounding against agent trajectory | YES | HIGH |
| L7 | BIAS_MITIGATION | Discriminatory or unfair content in output | YES | MEDIUM/HIGH |
| L8 | OUTPUT_VALIDATION | Format, required fields, length, prohibited phrases, regex rules | YES | HIGH |
| L9 | AUDIT_LOGGING | Full request/response audit trail with hashed content | **NO — async** | N/A |
| L10 | MONITORING_ALERTING | Anomaly detection, rate spike, violation rate | **NO — async** | Generates `MonitoringAlert` |
| L11 | ENCRYPTION | Symmetric encryption of sensitive data at rest | On-demand | N/A |
| L12 | COMPLIANCE_REPORTING | HIPAA, PCI-DSS, SOC2, GDPR, CCPA, FERPA framework mapping | **NO — async** | N/A |

### Blocking Behavior (from `guardrail_manager.py` lines 248–263)

```
CRITICAL violation   → blocked = True (always)
HIGH violation       → blocked = True only if config.block_on_high = True
MEDIUM/LOW violation → allow, log only
```

All primary layers continue to run even after a block is triggered — ensuring a complete audit trail even for blocked requests.

### Risk Score Calculation (lines 341–353)

| Severity | Weight |
|----------|--------|
| LOW | 0.1 |
| MEDIUM | 0.3 |
| HIGH | 0.6 |
| CRITICAL | 1.0 |

Final score = `min(1.0, sum(weights) / 2.0)`. Range: 0.0–1.0. Exposed via `GuardrailResult.risk_score`.

---

## Guardrail Code Review Checklist

### 1. Pipeline Completeness (CRITICAL)

- [ ] Input validation layer present — type, length, format checks before any LLM call
- [ ] Prompt injection detection layer present — specifically guards against instruction override and jailbreak attempts
- [ ] Content filtering layer present on both input and output paths
- [ ] Output validation layer present — agent output is validated, not just user input
- [ ] At minimum: L1, L4, L5, L8 must exist for any LLM-facing endpoint

### 2. Prompt Injection Defense (CRITICAL)

- [ ] Input is checked for instruction-override patterns before reaching the LLM
- [ ] System prompt is immutable — user input cannot overwrite system instructions
- [ ] Tool call arguments are validated independently of the raw user prompt
- [ ] Agent trajectory (tool inputs/outputs) is logged and available for hallucination detection at L6
- [ ] Indirect injection vectors covered: URL content, file content, database values fed into prompts

### 3. PII Handling (HIGH)

- [ ] PII detection runs on both input (L2) and output (content filter L5)
- [ ] PII is redacted before logging — audit log stores `input_hash`/`output_hash`, not raw content (see `AuditLogEntry` in `models.py` lines 181–182)
- [ ] All PII types configured: SSN, credit card, phone, email, address, DOB, drivers license, passport, bank account, IP address
- [ ] `pii_redact = True` in `GuardrailConfig` — never set to `False` in production
- [ ] PII is not echoed back in agent responses

### 4. Output Validation (HIGH)

- [ ] Output validator defines both positive rules (required content) and negative rules (prohibited phrases)
- [ ] Domain-specific validators exist (e.g., `weather_validator`, `hurricane_validator` in `output_validator.py`)
- [ ] Validation rules cover: minimum/maximum length, prohibited placeholders (`[TODO]`, `[insert`), required data patterns
- [ ] Pass threshold set at >= 0.75 for domain validators; >= 0.80 for safety-critical domains (hurricane)
- [ ] Validation failures are surfaced as violations, not silently ignored

### 5. Constitutional AI Principles (HIGH)

- [ ] A `Constitution` is defined with domain-specific principles (see `constitutional_ai.py`)
- [ ] Principles cover all required categories: SAFETY, ACCURACY, HELPFULNESS, HONESTY, HARMLESSNESS, PRIVACY, FAIRNESS
- [ ] SAFETY principles have `weight = 1.0` (maximum) — never reduce safety principle weight
- [ ] `pass_threshold` for constitutional validation is >= 0.8
- [ ] `max_iterations` for critique-revision cycles is >= 1 (at least one revision attempt)
- [ ] LLM fallback to heuristic critique is implemented — constitutional validation must not throw if LLM is unavailable

### 6. Async Audit Logging (HIGH)

- [ ] L9 (AUDIT_LOGGING) and L10 (MONITORING_ALERTING) run in `COMMON_LAYERS` — never in blocking `INPUT_LAYER_ORDER` or `OUTPUT_LAYER_ORDER`
- [ ] `parallel_execution = True` for audit/monitoring layers — they must not add latency to the user response path
- [ ] Audit log entries hash content (`input_hash`, `output_hash`) — raw user input is never stored in plain text in audit logs
- [ ] `retention_days = 2555` (7 years) set on `AuditLogEntry` for compliance frameworks
- [ ] Audit log failures do NOT block the response — `asyncio.gather(*common_tasks, return_exceptions=True)` pattern required

### 7. Life-Safety and Emergency Path (CRITICAL, when applicable)

- [ ] Emergency/life-safety queries bypass cache — never return stale data for hurricane warnings, flood alerts, or evacuation guidance
- [ ] Constitutional AI `weather_harmless_1` principle (`weight=1.0`) blocks any response that downplays severe weather risks
- [ ] Dangerous advice patterns explicitly prohibited in content filter: "don't evacuate", "ignore warning", "safe to stay", "drive through flood"
- [ ] Hurricane category-wind speed alignment validated (Saffir-Simpson: Cat1=74-95 mph, Cat5=157+ mph)
- [ ] Life-safety violations generate CRITICAL severity, not HIGH

### 8. Configuration Security (HIGH)

- [ ] `block_on_high = True` in production `GuardrailConfig` — never set to `False` without documented justification
- [ ] `block_on_critical = True` always — this flag must never be disabled in production
- [ ] `enabled_layers` includes all 12 layers in production — partial layer sets only acceptable for non-production environments
- [ ] `timeout_ms` is set (default 1000ms) — guardrail checks must not run unbounded
- [ ] `prohibited_topics` list is populated for domain-specific agents, not left empty

### 9. Risk Score Exposure (MEDIUM)

- [ ] `GuardrailResult.risk_score` is exposed via API response metadata or monitoring
- [ ] Risk score tracked in monitoring layer for anomaly detection
- [ ] Alerts generated when risk scores trend above threshold (L10 `MONITORING_ALERTING`)
- [ ] Risk score logged with each request in the audit trail

### 10. Compliance Framework Mapping (MEDIUM, when regulated)

- [ ] Applicable `ComplianceFramework` values declared in `GuardrailConfig.compliance_frameworks`
- [ ] L12 (COMPLIANCE_REPORTING) enabled for regulated workloads (HIPAA, PCI-DSS, GDPR, CCPA)
- [ ] Compliance report generated and stored at required intervals
- [ ] `AuditLogEntry.compliance_frameworks` populated on each log entry

---

## Anti-Patterns to Flag

### CRITICAL

- **Synchronous audit logging in the blocking path** — audit/monitoring layers added to `INPUT_LAYER_ORDER` or `OUTPUT_LAYER_ORDER` instead of `COMMON_LAYERS`. This directly adds latency to every user response.
- **Missing output validation** — only L1–L5 (input layers) are implemented with no L6–L8 (output layers). Agents can produce harmful, hallucinated, or malformed responses with no check.
- **`block_on_critical = False`** — no CRITICAL violation should ever be allowed through in production.
- **Caching life-safety responses** — returning cached responses for emergency or evacuation queries. Cache must be bypassed for safety-critical paths.

### HIGH

- **Single-layer guardrails** — one content filter with no injection detection, output validation, or constitutional check. A single regex-based filter is trivially bypassed by rephrasing.
- **Silent guardrail failures** — exceptions in guardrail layer code are swallowed and treated as "pass". Any error in a guardrail layer must surface as a violation or block, not a silent success.
- **PII in audit logs** — storing raw user input or raw agent output in audit logs without hashing. `AuditLogEntry` must use `input_hash`/`output_hash` fields, never raw strings.
- **`pii_redact = False` in production** — PII detection without redaction is monitoring, not protection.

### MEDIUM

- **No trajectory context at output check** — calling `check_output()` without passing `trajectory` means L6 (hallucination detection) cannot verify response grounding against tool call results.
- **Constitutional AI with no LLM and no heuristics** — returning all principles as "passing" when neither LLM nor heuristic critique is available.
- **Empty `prohibited_topics` for domain agents** — domain-specific agents (weather, finance, medical) must define explicit topic prohibitions, not rely solely on content filter patterns.
- **`max_input_length` unconfigured** — leaving the default (10,000 chars) without validating it is appropriate for the deployment context. Prompt injection via very long inputs is a known vector.

---

## Integration with LangGraph

### Where to Place Guardrails in the Graph

```
[User Input Node]
      |
      v
[Guardrail: check_input()]   <-- L1-L5 run here, before any LLM call
      |
      | (passed)
      v
[LLM / Agent Node(s)]
      |
      v
[Tool Call Nodes]            <-- trajectory accumulated here
      |
      v
[Guardrail: check_output()]  <-- L6-L8 run here, with trajectory passed
      |
      | (passed)
      v
[Response to User]
```

### HITL (Human-in-the-Loop) Interaction

- HITL interrupt nodes should be placed AFTER `check_input()` passes but BEFORE the LLM node — human review of flagged-but-not-blocked inputs is cheaper than reviewing LLM outputs
- If `GuardrailResult.blocked = True`, route to a rejection node rather than a HITL node — blocked requests should not consume human reviewer capacity
- HITL approval does NOT bypass output guardrails — `check_output()` must still run on HITL-approved responses before delivery to the user
- Risk score from `GuardrailResult.risk_score` can be used to threshold HITL triggers: e.g., score > 0.3 → HITL review, score > 0.6 → auto-block

### State Schema Requirements

The LangGraph state schema for agents with guardrails must include:

```python
class AgentState(TypedDict):
    query: str
    trajectory: list[dict]      # Tool calls + results — required for L6 hallucination check
    guardrail_input_result: GuardrailResult | None
    guardrail_output_result: GuardrailResult | None
    blocked: bool
    risk_score: float
```

---

## Severity Reference

| Label | Meaning |
|-------|---------|
| CRITICAL | Hard block — zero tolerance; escalate to human immediately |
| HIGH | Block if `block_on_high = True`; flag for review in all cases |
| MEDIUM | Allow with elevated monitoring; trend tracking required |
| LOW | Allow; log only |
