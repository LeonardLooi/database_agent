# Terraform CI/CD — GitHub Actions

> GitHub Actions ONLY — never generate `cloudbuild.yaml` (workspace rule).

## Full Pipeline

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  pull_request:
    paths: ['terraform/**']
  push:
    branches: [main]
    paths: ['terraform/**']

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "~> 1.9.0"
      - name: Format check
        run: terraform fmt -check -recursive terraform/
      - name: Validate modules
        run: |
          for dir in terraform/modules/*/; do
            echo "Validating $dir"
            terraform -chdir="$dir" init -backend=false
            terraform -chdir="$dir" validate
          done
      - name: tflint
        uses: terraform-linters/setup-tflint@v4
      - name: tfsec
        uses: aquasecurity/tfsec-action@v1.0.0
        with:
          working_directory: terraform/

  test:
    needs: validate
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "~> 1.9.0"
      - name: Native terraform test (mock providers — no GCP auth required)
        run: |
          for dir in terraform/modules/*/; do
            echo "Testing $dir"
            terraform -chdir="$dir" init -backend=false
            terraform -chdir="$dir" test
          done

  plan:
    needs: test
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.WIF_PROVIDER }}
          service_account: ${{ vars.TERRAFORM_SA }}
      - uses: hashicorp/setup-terraform@v3
      - name: Terraform Plan (staging)
        run: |
          cd terraform/environments/staging
          terraform init
          terraform plan -out=tfplan

  apply:
    needs: plan
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.WIF_PROVIDER }}
          service_account: ${{ vars.TERRAFORM_SA }}
      - uses: hashicorp/setup-terraform@v3
      - name: Terraform Apply (staging)
        run: |
          cd terraform/environments/staging
          terraform init
          terraform apply -auto-approve
```

**Stage order enforced:** `validate -> test -> plan -> apply`. Never skip test stage.
