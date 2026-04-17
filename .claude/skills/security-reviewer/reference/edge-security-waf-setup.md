# Edge Security / WAF Setup — Cloud-Agnostic Pattern

## Architecture

```
Client -> External Load Balancer -> WAF/Security Policy -> Backend (Serverless/Container)
```

All production APIs MUST have an edge security layer between the internet and your application. Application-level rate limiting alone is insufficient — volumetric attacks must be stopped at the edge before consuming compute resources.

## GCP Implementation: Load Balancer + Cloud Armor + Cloud Run

### 1. Serverless Network Endpoint Group (NEG)

Connect Cloud Run to the load balancer:

```hcl
resource "google_compute_region_network_endpoint_group" "api_neg" {
  name                  = "${var.service_name}-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.api.name
  }
}
```

### 2. Backend Service

```hcl
resource "google_compute_backend_service" "api_backend" {
  name                  = "${var.service_name}-backend"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  security_policy       = google_compute_security_policy.api_waf.id

  backend {
    group = google_compute_region_network_endpoint_group.api_neg.id
  }

  log_config {
    enable = true
  }
}
```

### 3. Cloud Armor Security Policy (WAF)

```hcl
resource "google_compute_security_policy" "api_waf" {
  name = "${var.service_name}-waf"

  # Rule 1: OWASP ModSecurity Core Rule Set
  rule {
    action   = "deny(403)"
    priority = 100
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-v33-stable')"
      }
    }
    description = "Block XSS attacks"
  }

  rule {
    action   = "deny(403)"
    priority = 200
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-v33-stable')"
      }
    }
    description = "Block SQL injection"
  }

  # Rule 2: Rate limiting (100 req/min per IP)
  rule {
    action   = "throttle"
    priority = 1000
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
    rate_limit_options {
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      conform_action = "allow"
      exceed_action  = "deny(429)"
    }
    description = "Rate limit all IPs"
  }

  # Rule 3: Geo-blocking (allow only target regions)
  rule {
    action   = "deny(403)"
    priority = 2000
    match {
      expr {
        expression = "origin.region_code != 'US' && origin.region_code != 'CA' && origin.region_code != 'GB'"
      }
    }
    description = "Geo-block non-target regions (adjust per product)"
  }

  # Rule 4: IP deny list (manually maintained)
  rule {
    action   = "deny(403)"
    priority = 500
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = var.blocked_ips }
    }
    description = "Block known bad IPs"
  }

  # Default: allow
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
    description = "Default allow"
  }
}
```

### 4. HTTPS Frontend

```hcl
resource "google_compute_global_forwarding_rule" "api_https" {
  name                  = "${var.service_name}-https"
  target                = google_compute_target_https_proxy.api.id
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.api.id
}

resource "google_compute_managed_ssl_certificate" "api" {
  name = "${var.service_name}-cert"
  managed {
    domains = [var.api_domain]
  }
}
```

### 5. Restrict Cloud Run to Load Balancer Only

Prevent direct access to the Cloud Run URL — all traffic must go through the load balancer:

```hcl
resource "google_cloud_run_v2_service" "api" {
  # ...
  ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
}
```

## Cloud-Agnostic Checklist

Regardless of cloud provider, verify these controls exist:

- [ ] External load balancer terminates TLS
- [ ] WAF rules block XSS, SQLi, and common attack patterns
- [ ] Rate limiting at edge (before application layer)
- [ ] Geo-blocking configured for non-target regions
- [ ] IP deny list mechanism available
- [ ] Backend accessible ONLY through the load balancer (no direct URL access)
- [ ] Access logs enabled on load balancer
- [ ] DDoS protection enabled (GCP: Cloud Armor adaptive protection)
- [ ] HTTPS-only (HTTP redirects to HTTPS)
- [ ] Security headers added at edge or application layer

## AWS Equivalent

| GCP Component | AWS Equivalent |
|---------------|---------------|
| Cloud Armor | AWS WAF |
| External LB | ALB / CloudFront |
| Serverless NEG | Lambda integration / Fargate target group |
| Cloud Run | ECS Fargate / Lambda |

## When to Use

- ANY production API exposed to the internet
- Before first production deployment (not after an incident)
- When scaling beyond a single instance (rate limiting needs shared state)
