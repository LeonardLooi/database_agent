---
name: gcp-finops
description: "GCP cost optimization and resilience skill. Use for GCP billing budget alerts, committed use discounts, sustained use discounts, cost allocation labels, GCP Recommender, Cloud SQL PITR, multi-region DR, and RTO/RPO planning. Triggers: GCP cost, billing, committed use discount, sustained use discount, cost optimization GCP, DR planning, RTO, RPO, disaster recovery GCP."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
metadata:
  triggers: ["GCP cost", "billing alert", "committed use discount", "CUD", "sustained use discount", "cost optimization GCP", "DR planning GCP", "RTO", "RPO", "disaster recovery GCP", "GCP Recommender", "FinOps GCP"]
  related-skills: [gcp-cloud-run, architecture-design, terraform-specialist, deployment-engineer]
  domain: infrastructure
  role: specialist
  scope: operations
  output-format: document
last-reviewed: "2026-03-14"
---

# GCP FinOps

## Iron Law

```
NO GCP COST WORK WITHOUT:
1. Verifying cost allocation labels are applied to all resources (project, service, environment)
2. A billing budget alert configured before committing spend
3. Using terraform-specialist agent for Committed Use Discount reservations (never manual console)
```

---

## This Skill vs Related Agents

| Task | Use This Skill | Use Which Agent |
|------|---------------|-----------------|
| Cost analysis, Recommender review | YES | — |
| Right-sizing Cloud Run services | YES + | `deployment-engineer` |
| CUD / Spend-based reservations (Terraform) | NO | `terraform-specialist` |
| Billing budget Terraform resource | YES (pattern here) | `terraform-specialist` (apply) |
| DR runbook, RTO/RPO planning | YES | — |
| Multi-region Cloud Run deploy pipeline | NO | `deployment-engineer` |
| Cloud SQL HA Terraform config | YES (pattern here) | `terraform-specialist` (apply) |

---

## Pattern Selector

```
What do you need?
    |
    +-- Reduce GCP spend / right-size resources?
    |   -> Load: reference/gcp-cost-optimization.md
    |   -> Section: Cloud Run Cost Optimization + Monthly Cost Audit Checklist
    |
    +-- Set up billing budget alerts?
    |   -> Load: reference/gcp-cost-optimization.md
    |   -> Section: GCP Billing Budget Alert (Terraform resource)
    |
    +-- Plan disaster recovery / set RTO+RPO targets?
    |   -> Load: reference/gcp-resilience-dr.md
    |   -> Section: RTO/RPO Targets by Tier
    |
    +-- Run GCP Recommender to find cost savings?
    |   -> Load: reference/gcp-cost-optimization.md
    |   -> Section: GCP Recommender — Cost Insights (gcloud commands)
    |
    +-- Cloud SQL HA or PITR recovery?
        -> Load: reference/gcp-resilience-dr.md
        -> Section: Cloud SQL High Availability + PITR Recovery
```

---

## GCP Cost Tools — Quick Reference

- **GCP Billing Console** — `console.cloud.google.com/billing` — cost breakdown by project, service, label
- **Cloud Cost Management** — cost table, cost breakdown report, budget history
- **GCP Recommender** — automated right-sizing, idle resource, and CUD recommendations (`gcloud recommender`)
- **Active Assist** — umbrella for all Recommender signals; surfaces in Cloud Console dashboard
- **Committed Use Discounts** — 1-yr (~37% off) or 3-yr (~55% off); resource-based or spend-based
- **Sustained Use Discounts** — automatic for Compute Engine VMs running >25% of month; no action needed

Deep patterns, gcloud snippets, and Terraform resources → reference files below.

---

## Reference Files

| File | Load When |
|------|-----------|
| `reference/gcp-cost-optimization.md` | Cost analysis, CUD/SUD, Cloud Run sizing, billing budgets, Recommender, label enforcement, monthly audit |
| `reference/gcp-resilience-dr.md` | RTO/RPO planning, Cloud SQL HA + PITR, multi-region Cloud Run, Global LB failover, Firestore multi-region, DR runbook |

---

## Cross-References

- **Terraform resources (CUD, budgets, SQL HA)**: Dispatch `terraform-specialist` agent to apply patterns from reference files
- **Cloud Run deployment / right-sizing**: Use `deployment-engineer` agent with sizing flags from `reference/gcp-cost-optimization.md`
- **Architecture decisions (multi-region)**: Use `architecture-design` skill + `architect` agent for ADR
- **Security review (WIF, IAM)**: Dispatch `security-reviewer` after any infrastructure change
- **Cloud Run functions**: See `gcp-cloud-run` skill
