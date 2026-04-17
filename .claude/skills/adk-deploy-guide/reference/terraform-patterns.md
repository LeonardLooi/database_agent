# Custom Infrastructure (Terraform)

> Assumes scaffolded projects with `deployment/terraform/` directories.

## CRITICAL Rule

**NEVER create GCP resources manually via `gcloud` for production. Define all infrastructure in Terraform.**

Exception: quick experimentation is fine with `gcloud` or console for throwaway resources. Production infrastructure — Cloud SQL, Pub/Sub, Eventarc, BigQuery, service accounts, IAM — must be in Terraform.

---

## Where to Put Custom Terraform

| Scenario | Location |
|----------|----------|
| Dev-only infrastructure | `deployment/terraform/dev/` |
| CI/CD environments (staging + prod) | `deployment/terraform/` |

Resources in `deployment/terraform/` are applied to **both** staging and prod projects. Use `for_each` with `local.deploy_project_ids` for multi-environment resources.

---

## Common Resource Patterns

### Pub/Sub Topic + Push Subscription

```hcl
# deployment/terraform/dev/custom_resources.tf
resource "google_pubsub_topic" "events" {
  name    = "${var.project_name}-events"
  project = var.dev_project_id
}

resource "google_pubsub_subscription" "trigger" {
  topic = google_pubsub_topic.events.id
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.app.uri}/apps/my_agent/trigger/pubsub"
    oidc_token {
      service_account_email = google_service_account.app_sa.email
      audience              = google_cloud_run_v2_service.app.uri
    }
  }
  ack_deadline_seconds = 30
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "60s"
  }
}
```

### Eventarc Trigger (Cloud Storage)

```hcl
resource "google_eventarc_trigger" "storage_trigger" {
  name     = "${var.project_name}-storage-trigger"
  location = var.region
  project  = var.dev_project_id

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.uploads.name
  }

  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.app.name
      region  = var.region
      path    = "/invoke"
    }
  }

  service_account = google_service_account.app_sa.email
}
```

### BigQuery Dataset

```hcl
resource "google_bigquery_dataset" "analytics" {
  dataset_id = "${replace(var.project_name, "-", "_")}_analytics"
  project    = var.dev_project_id
  location   = var.region
}
```

---

## IAM Bindings

Always bind IAM via Terraform — never `gcloud projects add-iam-policy-binding` for production.

```hcl
# Pub/Sub publisher
resource "google_pubsub_topic_iam_member" "app_publisher" {
  topic   = google_pubsub_topic.events.name
  project = var.dev_project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

# BigQuery data editor
resource "google_bigquery_dataset_iam_member" "app_editor" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  project    = var.dev_project_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.app_sa.email}"
}

# Pub/Sub service agent token creation (for push subscriptions)
resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.app_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
```

> IAM propagation is not instant — wait ~2 minutes after granting a role before retrying. Do not re-grant the same role repeatedly.

---

## Applying Custom Infrastructure

```bash
# Dev environment only
make setup-dev-env   # runs terraform apply in deployment/terraform/dev/

# Staging + prod — applied automatically by CI/CD pipeline on push to main
```

---

## Terraform State Management

### Remote State (Default)

`setup-cicd` creates a GCS bucket for remote Terraform state:

```hcl
# deployment/terraform/backend.tf (auto-configured)
terraform {
  backend "gcs" {
    bucket = "{cicd_project}-terraform-state"
    prefix = "{repository_name}/{prod|dev}"
  }
}
```

State is isolated per project and environment using the repository name + environment prefix.

### Local State

Use `--local-state` with `setup-cicd` for single-developer projects:

```bash
uvx agent-starter-pack setup-cicd \
  --staging-project STAGING_PROJECT \
  --prod-project PROD_PROJECT \
  --local-state
```

State stored in `deployment/terraform/terraform.tfstate`. Not suitable for teams (state conflicts).

---

## Importing Existing Resources

If resources already exist (created manually or by a previous deployment), import them before running `terraform apply`:

```bash
cd deployment/terraform/dev

# Cloud Run service
terraform import google_cloud_run_v2_service.app \
  projects/PROJECT_ID/locations/REGION/services/SERVICE_NAME

# Service account
terraform import google_service_account.app_sa \
  projects/PROJECT_ID/serviceAccounts/SA_EMAIL

# Secret Manager secret
terraform import google_secret_manager_secret.my_secret \
  projects/PROJECT_ID/secrets/SECRET_NAME

# Pub/Sub topic
terraform import google_pubsub_topic.events \
  projects/PROJECT_ID/topics/TOPIC_NAME
```

After importing, run `terraform plan` to verify state matches configuration. Fix any drift before applying.

> Resources created via `null_resource` + `local-exec` (e.g., BigQuery linked datasets) won't appear in `gcloud` output — check `terraform state list` to see what Terraform actually manages.
