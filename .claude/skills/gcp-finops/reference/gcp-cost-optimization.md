# GCP Cost Optimization Reference

## Sustained Use Discounts (SUD)

- Automatic for Compute Engine VMs running >25% of a month — no action required
- Discount scales linearly: 25% usage = ~10% off, 100% usage = ~30% off
- **Does NOT apply to:** Cloud Run, Cloud SQL, GKE Autopilot, preemptible/spot VMs
- **Action:** None — GCP applies automatically. Verify in Billing Console under "Credits".

---

## Committed Use Discounts (CUD)

| Type | Savings | Flexibility |
|------|---------|-------------|
| Resource-based CUD (1-year) | ~37% off | Commits to specific machine type + region |
| Resource-based CUD (3-year) | ~55% off | Same as above, longer term |
| Spend-based CUD (1-year) | ~25% off | Commits to $ amount — flexible across machine types |

**When to use resource-based vs spend-based:**
- Resource-based: you have stable, predictable VM workloads on a specific machine type
- Spend-based: mixed VM fleet or you need flexibility to change machine types

**Terraform — 1-year resource-based CUD:**

```hcl
resource "google_compute_commitment" "api_commitment" {
  name   = "api-cud-1yr"
  region = "us-central1"
  plan   = "TWELVE_MONTH"

  resources {
    type   = "VCPU"
    amount = "8"
  }
  resources {
    type   = "MEMORY"
    amount = "32768"  # MB
  }
}
```

**Warning:** CUD reservations are binding — you pay whether or not you use the capacity.
Always dispatch `terraform-specialist` to apply; never create CUDs via GCP Console.

---

## Cloud Run Cost Optimization

Cloud Run billing = CPU + memory + request count. Key levers:

| Flag | Dev/Staging | Prod | Reason |
|------|-------------|------|--------|
| `--min-instances` | `0` | `1` (if cold start SLA) | 0 = no idle cost |
| `--max-instances` | `5` | `20–50` | Cap runaway scaling spend |
| `--concurrency` | `80` (default) | `80` | Maximize per-instance utilization |
| `--cpu` | `1` | `1–2` | 1 for Python/Node; Spring Boot needs 2 under load |
| `--memory` | `512Mi` | `512Mi`–`1Gi` | Python/Node: 512Mi; Spring Boot: 1Gi |
| `--cpu-throttling` | default (on) | default (on) | CPU only allocated during requests — DO NOT disable unless background workers |

**`--no-cpu-throttling`**: Only for long-running background workers that need CPU between requests.
Setting this on an HTTP service doubles your CPU bill for zero benefit.

**Right-sizing example (gcloud):**
```bash
gcloud run services update my-service \
  --region us-central1 \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 20 \
  --concurrency 80
```

---

## Cost Allocation Labels

All GCP resources must have these labels. Enforced via Organization Policy.

**Required labels:**
- `environment` — `dev`, `staging`, `prod`
- `team` — owning team (e.g., `backend`, `platform`)
- `service` — service name (e.g., `payments`, `auth`)
- `cost-center` — billing allocation unit (e.g., `eng`, `data`)

**Apply to Cloud Run service (gcloud):**
```bash
gcloud run services update my-service \
  --region us-central1 \
  --update-labels environment=prod,team=backend,service=payments,cost-center=eng
```

**Terraform — reusable label pattern:**
```hcl
locals {
  common_labels = {
    environment  = var.environment
    team         = var.team
    service      = var.service_name
    cost-center  = var.cost_center
    managed-by   = "terraform"
  }
}

resource "google_cloud_run_v2_service" "api" {
  # ...
  labels = local.common_labels
}

resource "google_sql_database_instance" "db" {
  # ...
  settings {
    user_labels = local.common_labels
  }
}
```

---

## GCP Billing Budget Alert

Set this up BEFORE committing spend on any new service or environment.

```hcl
resource "google_billing_budget" "service_budget" {
  billing_account = var.billing_account_id
  display_name    = "${var.service_name}-monthly-budget"

  budget_filter {
    projects = ["projects/${var.project_id}"]
    labels = {
      service = var.service_name
    }
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = "500"
    }
  }

  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    pubsub_topic = google_pubsub_topic.billing_alerts.id
  }
}
```

**Note:** `all_updates_rule.pubsub_topic` requires a Pub/Sub topic. Wire this to a Cloud Run Function
or a notification channel (Slack, PagerDuty) to make alerts actionable.

---

## GCP Recommender — Cost Insights

GCP Recommender surfaces automated savings recommendations. Run these monthly.

**Cost optimization recommendations (billing-level):**
```bash
gcloud recommender recommendations list \
  --project=$PROJECT_ID \
  --location=global \
  --recommender=google.billing.CostInsightRecommender \
  --format="table(name,recommenderSubtype,stateInfo.state,primaryImpact.costProjection.cost.units)"
```

**VM right-sizing recommendations:**
```bash
gcloud recommender recommendations list \
  --project=$PROJECT_ID \
  --location=us-central1 \
  --recommender=google.compute.instance.MachineTypeRecommender
```

**Idle VM recommendations:**
```bash
gcloud recommender recommendations list \
  --project=$PROJECT_ID \
  --location=us-central1 \
  --recommender=google.compute.instance.IdleResourceRecommender
```

**Apply a recommendation (after review):**
```bash
gcloud recommender recommendations mark-claimed \
  projects/$PROJECT_ID/locations/us-central1/recommenders/google.compute.instance.MachineTypeRecommender/recommendations/RECOMMENDATION_ID \
  --etag=ETAG \
  --state-metadata=reviewedBy=finops-team
```

---

## Monthly Cost Audit Checklist

Run this at the start of each month:

- [ ] Run Recommender — apply all HIGH-priority cost recommendations
- [ ] Review Cloud Run `--min-instances` — are any staging services set to min=1? Set to 0.
- [ ] Check for idle Cloud SQL instances — no connections in 7 days → evaluate shutdown
- [ ] Verify cost allocation labels on all Cloud Run services and Cloud SQL instances
- [ ] Review committed use discount utilization in Billing Console — target >80% utilization
- [ ] Check Cloud Storage lifecycle policies — objects older than 30 days should move to Nearline; 90 days → Coldline; 365 days → Archive (unless access pattern requires otherwise)
- [ ] Review `--max-instances` caps — are any services uncapped or set too high?
- [ ] Check for orphaned Artifact Registry images older than 90 days
