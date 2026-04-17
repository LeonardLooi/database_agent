# Threat Mitigation Mapping Reference

Map identified threats to security controls for effective defense planning.

## Control Categories

| Category | Description | Purpose | Examples |
|----------|-------------|---------|---------|
| **Preventive** | Controls that stop attacks before they succeed | Block or deter | Firewall, input validation, MFA, encryption, RBAC |
| **Detective** | Controls that identify attacks in progress or after the fact | Detect and alert | IDS/IPS, log monitoring, anomaly detection, SIEM |
| **Corrective** | Controls that respond to and recover from attacks | Contain and restore | Incident response, backup restore, circuit breakers, rollback |

## Control Layers

| Layer | Description | Example Controls |
|-------|-------------|-----------------|
| **Network** | Perimeter and internal network defenses | Firewall, WAF, DDoS protection, network segmentation, TLS |
| **Application** | Code-level and runtime protections | Input validation, authentication, authorization, CSP, parameterized queries |
| **Data** | Protection of data at rest and in transit | Encryption (AES-256), access controls, data classification, key management |
| **Endpoint** | Device and host-level security | EDR, patch management, host hardening, antivirus |
| **Process** | People and procedure controls | Security training, incident response plans, access reviews, secure SDLC |

## Control Library

| Control | Threats Mitigated | Effectiveness | Implementation Effort |
|---------|-------------------|---------------|----------------------|
| Multi-Factor Authentication | Spoofing | High | Medium |
| Input Validation Framework | Tampering, Injection | High | Medium |
| Web Application Firewall | Tampering, DoS, Injection | Medium | Medium |
| Data Encryption at Rest | Information Disclosure | High | Medium |
| TLS 1.3 Encryption | Information Disclosure, Tampering | High | Low |
| Security Event Logging | Repudiation | Medium | Low |
| Log Integrity Protection | Repudiation, Tampering | Medium | Medium |
| Role-Based Access Control | Elevation of Privilege, Info Disclosure | High | Medium |
| Rate Limiting | Denial of Service | Medium | Low |
| DDoS Protection Service | Denial of Service | High | High |
| Account Lockout Policy | Spoofing | Medium | Low |
| Content Security Policy | Tampering (XSS) | Medium | Low |
| Parameterized Queries | Tampering (SQLi) | High | Low |
| API Response Filtering | Information Disclosure | Medium | Low |
| Circuit Breakers | Denial of Service | Medium | Low |
| Automated Backup + Restore | All (recovery) | High | Medium |

## Coverage Scoring

### Formula

```
coverage_score = effectiveness x status_multiplier
```

### Status Multipliers

| Implementation Status | Multiplier |
|----------------------|------------|
| Implemented and verified | 1.0 |
| Implemented (not verified) | 0.8 |
| Partially implemented | 0.5 |
| Planned (not started) | 0.2 |
| Not planned | 0.0 |

### Effectiveness Scale

| Rating | Value | Meaning |
|--------|-------|---------|
| Very High | 4 | Blocks the threat in nearly all scenarios |
| High | 3 | Blocks the threat in most scenarios |
| Medium | 2 | Reduces risk significantly but bypassable |
| Low | 1 | Provides minimal protection |

### Example Calculation

```
Control: MFA (effectiveness=3, status=Implemented and verified)
coverage_score = 3 x 1.0 = 3.0

Control: WAF (effectiveness=2, status=Partially implemented)
coverage_score = 2 x 0.5 = 1.0

Threat total coverage = sum of all control scores for that threat
```

## Defense-in-Depth Validation Checklist

For each identified threat, validate that mitigations satisfy defense-in-depth:

- [ ] **Multiple layers** -- Controls span at least 2 different layers (e.g., Network + Application)
- [ ] **Multiple types** -- Controls include at least 2 categories (e.g., Preventive + Detective)
- [ ] **No single point of failure** -- Bypassing one control does not eliminate all protection
- [ ] **Detection capability** -- At least one detective control exists to alert on bypass of preventive controls
- [ ] **Recovery path** -- At least one corrective control exists for incident response
- [ ] **Trust boundary coverage** -- Every trust boundary crossing has at least one control

### Validation Failures

If any checklist item fails:
1. Flag the gap in the threat model
2. Recommend specific controls to close the gap
3. Prioritize based on the threat's risk score

## Budget Prioritization

When resources are limited, rank control investments by value:

### Prioritization Formula

```
priority_score = (threats_covered x effectiveness) / implementation_cost
```

Where:
- `threats_covered` = number of distinct threats this control mitigates
- `effectiveness` = effectiveness rating (1-4)
- `implementation_cost` = estimated cost rating (1=Low, 2=Medium, 3=High)

### Prioritization Strategy

1. **Start with high-value, low-cost controls** -- Input validation, TLS, logging, rate limiting
2. **Then high-value, medium-cost controls** -- MFA, RBAC, encryption at rest
3. **Then gap-filling controls** -- Controls needed for defense-in-depth even if lower individual value
4. **Last: high-cost controls** -- DDoS services, WAF appliances, EDR platforms

### Example Rankings

| Control | Threats Covered | Effectiveness | Cost | Priority Score |
|---------|----------------|---------------|------|----------------|
| Input Validation | 3 | 3 (High) | 2 (Med) | 4.5 |
| TLS 1.3 | 2 | 3 (High) | 1 (Low) | 6.0 |
| Security Logging | 2 | 2 (Med) | 1 (Low) | 4.0 |
| Rate Limiting | 1 | 2 (Med) | 1 (Low) | 2.0 |
| MFA | 1 | 3 (High) | 2 (Med) | 1.5 |
| DDoS Protection | 1 | 3 (High) | 3 (High) | 1.0 |

Higher priority score = implement first. Adjust based on actual cost estimates and threat severity.
