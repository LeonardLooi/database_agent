# Cloud Service Mapping — GCP Primary

> Use this when you know the AWS or Azure service name and need the GCP equivalent — or when selecting a GCP service for a new workload.
>
> **Workspace standard:** GCP is the primary cloud. AWS/Azure columns are reference only.

## Compute

| Use Case | GCP (Primary) | AWS Equivalent | Azure Equivalent |
|----------|--------------|----------------|-----------------|
| Managed containers (serverless) | **Cloud Run** | ECS Fargate | Container Apps |
| Event-driven functions | **Cloud Run** (containerized) | Lambda | Functions |
| Kubernetes | **GKE** | EKS | AKS |
| VMs (IaaS) | Compute Engine | EC2 | Virtual Machines |
| Batch jobs | Cloud Batch | AWS Batch | Azure Batch |

**Workspace choice:** Cloud Run for all 4 stacks (Python FastAPI, NestJS, Spring Boot, TypeScript/Fastify). GKE only if workload needs persistent sidecar containers or complex networking.

## Storage

| Use Case | GCP (Primary) | AWS Equivalent | Azure Equivalent |
|----------|--------------|----------------|-----------------|
| Object storage | **Cloud Storage** | S3 | Blob Storage |
| Block storage (VM disks) | Persistent Disk | EBS | Managed Disks |
| File storage (NFS) | Filestore | EFS | Azure Files |
| Cold/archive storage | Archive Storage class | S3 Glacier | Archive Storage |

**Workspace choice:** Cloud Storage for file uploads, static assets, and ML artifacts. Persistent Disk only for GKE workloads.

## Database

| Use Case | GCP (Primary) | AWS Equivalent | Azure Equivalent |
|----------|--------------|----------------|-----------------|
| Managed PostgreSQL | **Cloud SQL (PostgreSQL 16)** | RDS PostgreSQL | Azure Database for PostgreSQL |
| Serverless NoSQL | **Firestore** | DynamoDB | Cosmos DB |
| Distributed SQL (global) | Cloud Spanner | Aurora Global | Cosmos DB (multi-region) |
| In-memory cache | **Memorystore (Redis)** | ElastiCache | Azure Cache for Redis |
| Data warehouse | BigQuery | Redshift | Synapse Analytics |
| Vector search | **AlloyDB / pgvector on Cloud SQL** | Aurora pgvector | PostgreSQL Flexible Server |

**Workspace choice:** Cloud SQL (PostgreSQL) as primary relational DB. Firestore for Flutter mobile real-time sync. Memorystore for API caching.

## Messaging & Eventing

| Use Case | GCP (Primary) | AWS Equivalent | Azure Equivalent |
|----------|--------------|----------------|-----------------|
| Managed message queue (pub/sub) | **Pub/Sub** | SQS + SNS | Service Bus |
| Event streaming (Kafka-compatible) | **Pub/Sub** (or Confluent on GKE) | MSK (Kafka) | Event Hubs |
| Scheduled triggers | **Cloud Scheduler** | EventBridge Scheduler | Logic Apps |
| Event routing | **Eventarc** | EventBridge | Event Grid |
| Task queues (async jobs) | **Cloud Tasks** | SQS + Lambda | Service Bus + Functions |

**Workspace choice:** Pub/Sub for all async messaging between services. Cloud Tasks for delayed/retry-required jobs. Eventarc for Cloud Storage -> Cloud Run triggers.

## Security & Identity

| Use Case | GCP (Primary) | AWS Equivalent | Azure Equivalent |
|----------|--------------|----------------|-----------------|
| Secrets management | **Secret Manager** | Secrets Manager | Key Vault |
| IAM / RBAC | **Cloud IAM** | IAM | Azure AD RBAC |
| CI/CD auth (keyless) | **Workload Identity Federation** | OIDC for GitHub Actions | Federated Identity Credentials |
| API auth | **Firebase Auth / Identity Platform** | Cognito | Azure AD B2C |
| Vulnerability scanning | **Artifact Registry scanning** | ECR scanning | Container Registry |

**Workspace choice:** Secret Manager for all secrets. WIF for GitHub Actions (no service account JSON keys). Firebase Auth for mobile app authentication.

## Networking & CDN

| Use Case | GCP (Primary) | AWS Equivalent | Azure Equivalent |
|----------|--------------|----------------|-----------------|
| CDN | **Cloud CDN** | CloudFront | Azure CDN |
| Global load balancer | **Global External Application LB** | ALB + Global Accelerator | Application Gateway + Front Door |
| DNS | **Cloud DNS** | Route 53 | Azure DNS |
| VPC / private networking | **VPC** | VPC | Virtual Network |
| Private container registry | **Artifact Registry** | ECR | Azure Container Registry |

**Workspace choice:** Artifact Registry for all Docker images. Cloud DNS + Global LB for production APIs requiring global failover.

## Observability

| Use Case | GCP (Primary) | AWS Equivalent | Azure Equivalent |
|----------|--------------|----------------|-----------------|
| Structured logging | **Cloud Logging** | CloudWatch Logs | Azure Monitor Logs |
| Metrics + dashboards | **Cloud Monitoring** | CloudWatch Metrics | Azure Monitor |
| Distributed tracing | **Cloud Trace** | X-Ray | Application Insights |
| Error tracking | **Error Reporting** | None native | Application Insights |
| Profiling | **Cloud Profiler** | None native | None native |

**Workspace choice:** Cloud Logging + Cloud Monitoring + Cloud Trace as the standard observability stack. ADK agents add BigQuery Agent Analytics (see `adk-observability-guide` skill).

## IaC & Deployment

| Use Case | GCP (Primary) | AWS Equivalent | Azure Equivalent |
|----------|--------------|----------------|-----------------|
| Infrastructure as Code | **Terraform (google provider)** | CloudFormation / CDK | ARM / Bicep |
| CI/CD | **GitHub Actions** | GitHub Actions / CodePipeline | GitHub Actions / Azure DevOps |
| Container build | **Artifact Registry + Cloud Build** | ECR + CodeBuild | ACR + Azure Pipelines |

**Workspace choice:** Terraform + GitHub Actions exclusively. Never cloudbuild.yaml.
