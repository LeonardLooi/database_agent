---
name: stripe
description: Use when integrating Stripe payments in PropertyHarbor — subscription billing, customer management, payment links, webhooks, Stripe Connect vendor payouts, or invoicing. Load before writing any Stripe API code. Query the Stripe MCP server for API verification.
allowed-tools: Bash, Read, Write, Edit
metadata:
  triggers: Stripe, payment, billing, subscription, checkout, invoice, payout, payment link, pricing, Stripe Connect, webhook
  related-skills: revenuecat, python-dev, flutter-mobile
  domain: payments
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-30"
---

## Iron Law

**NO STRIPE API CALL WITHOUT WEBHOOK VERIFICATION — every payment mutation must have a corresponding webhook handler; never trust client-side payment confirmation alone**

# Stripe Payment Integration Skill

## MCP Server

The Stripe MCP server is configured in `.mcp.json` using the official `@stripe/mcp` npm package (stdio transport).

**Setup command (already configured in .mcp.json):**
```bash
claude mcp add stripe -- npx -y @stripe/mcp --tools=all --api-key=${STRIPE_SECRET_KEY}
```

**Alternative — Remote HTTP mode (OAuth, no API key in config):**
```bash
claude mcp add --transport http stripe https://mcp.stripe.com
```

**Configuration flags:**
- `--tools=all` — enable all 27 tools (default for PropertyHarbor)
- `--tools=customers.create,customers.read,...` — restrict to specific tools
- `--api-key=<key>` — Stripe secret key (prefer Restricted API Key `rk_*`)
- `--stripe-account=<acct_id>` — operate on a Stripe Connect connected account

**Fallback:** `context7` MCP → resolve `stripe` library docs.

### Available MCP Tools (27 total)

**Read-Only / Low-Risk (11 tools):**

| Tool | Description |
|------|-------------|
| `fetch_stripe_resources` | Retrieve Stripe objects by ID |
| `get_stripe_account_info` | Retrieve account information |
| `list_coupons` | List coupons |
| `list_customers` | List customers |
| `list_disputes` | List disputes |
| `list_prices` | List prices |
| `list_products` | List products |
| `list_setup_intents` | List SetupIntents |
| `retrieve_balance` | Retrieve account balance |
| `search_stripe_documentation` | Search Stripe knowledge base and docs |
| `search_stripe_resources` | Search Stripe resources (customers, charges, etc.) |

**Create Operations (5 tools):**

| Tool | Description |
|------|-------------|
| `create_coupon` | Create a coupon |
| `create_customer` | Create a customer |
| `create_price` | Create a price |
| `create_product` | Create a product |
| `update_dispute` | Update a dispute |

**Modify / Higher-Risk Operations (11 tools):**

| Tool | Description |
|------|-------------|
| `cancel_subscription` | Cancel a subscription |
| `create_invoice` | Create an invoice |
| `create_invoice_item` | Create an invoice item |
| `create_payment_link` | Create a payment link |
| `create_refund` | Create a refund |
| `finalize_invoice` | Finalize an invoice |
| `list_charges` | List charges |
| `list_invoices` | List invoices |
| `list_payment_intents` | List PaymentIntents |
| `list_subscriptions` | List subscriptions |
| `update_subscription` | Update a subscription |

**Tool permissions are controlled by your Restricted API Key (RAK).** Create one at the Stripe Dashboard → Developers → API Keys → Restricted Keys. Only grant the permissions each service actually needs.

## PropertyHarbor Context

PropertyHarbor uses Stripe for:
- **Subscription billing** — 3 tiers: Free ($0), Pro ($9/unit/mo), Growth ($7/unit/mo)
- **Vendor payouts** — Stripe Connect (Express accounts) for paying service vendors
- **One-time charges** — maintenance service invoicing to landlords
- RevenueCat handles mobile in-app subscription entitlements; Stripe is the backend payment processor

## Architecture Constraints

- **Backend only** — all Stripe API calls happen in Python/FastAPI services, never from Flutter clients
- **Webhook-first** — use Stripe webhooks as the source of truth for payment state, not API polling
- **Idempotency keys** — every mutating API call must include an idempotency key
- **Stripe Connect Express** — vendors onboard via Express accounts; PropertyHarbor is the platform
- **No PCI data in our DB** — never store card numbers, CVVs, or raw payment tokens in Cloud SQL
- **Restricted API Keys** — use `rk_*` keys scoped to minimum required permissions, not `sk_*` root keys
- **Environment variables** — `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_CONNECT_CLIENT_ID`

## Code Conventions

### Python (FastAPI backend)

```python
# Dependencies — add to service's pyproject.toml
# stripe==12.x.x (pin exact version)

import stripe
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

# Always configure from env, never hardcode
stripe.api_key = settings.STRIPE_SECRET_KEY

# Webhook verification — REQUIRED for all webhook endpoints
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Process event by type
    match event["type"]:
        case "checkout.session.completed":
            await handle_checkout_completed(event["data"]["object"])
        case "invoice.paid":
            await handle_invoice_paid(event["data"]["object"])
        case "customer.subscription.updated":
            await handle_subscription_updated(event["data"]["object"])

    return {"status": "ok"}
```

### Python (Agent Toolkit — for ADK integration)

```python
# For use inside Google ADK agents that need Stripe access
# pip install stripe-agent-toolkit (Python 3.11+)

from stripe_agent_toolkit import create_stripe_agent_toolkit

toolkit = await create_stripe_agent_toolkit(
    secret_key="rk_test_...",  # Restricted API Key
    configuration={
        "context": {
            "account": "acct_vendor_123"  # Optional: operate on Connect account
        }
    },
)
tools = toolkit.get_tools()
```

### Flutter (client-side)

```dart
// Flutter NEVER calls Stripe API directly
// Instead: Flutter → PropertyHarbor API → Stripe API
// Use flutter_stripe for Payment Sheet UI only

// Payment flow:
// 1. Flutter calls our backend to create PaymentIntent/SetupIntent
// 2. Backend returns client_secret
// 3. Flutter presents Stripe Payment Sheet with client_secret
// 4. Stripe handles PCI-compliant card collection
// 5. Webhook confirms payment on backend
```

## Webhook Events to Handle

| Event | Action |
|-------|--------|
| `checkout.session.completed` | Activate subscription, update user tier in Cloud SQL |
| `invoice.paid` | Record payment, extend subscription period |
| `invoice.payment_failed` | Flag account, send dunning notification |
| `customer.subscription.updated` | Sync plan changes to Cloud SQL + RevenueCat |
| `customer.subscription.deleted` | Downgrade to Free tier, revoke entitlements |
| `account.updated` (Connect) | Update vendor payout account status |
| `transfer.created` (Connect) | Record vendor payout in Cloud SQL |

## Stripe Connect (Vendor Payouts)

```python
# Vendor onboarding — create Express account
account = stripe.Account.create(
    type="express",
    country="US",
    email=vendor.email,
    capabilities={"transfers": {"requested": True}},
    idempotency_key=f"vendor-onboard-{vendor.id}",
)

# Create onboarding link
account_link = stripe.AccountLink.create(
    account=account.id,
    refresh_url=f"{BASE_URL}/vendors/stripe/refresh",
    return_url=f"{BASE_URL}/vendors/stripe/return",
    type="account_onboarding",
)

# Pay vendor after maintenance job completion
transfer = stripe.Transfer.create(
    amount=amount_cents,
    currency="usd",
    destination=vendor.stripe_account_id,
    transfer_group=f"ticket-{ticket_id}",
    idempotency_key=f"payout-ticket-{ticket_id}-vendor-{vendor.id}",
)
```

## Testing

```python
# Use Stripe test mode keys in development/CI
# STRIPE_SECRET_KEY=sk_test_... or rk_test_...

# Use Stripe CLI for local webhook testing:
# stripe listen --forward-to localhost:8000/webhooks/stripe

# Fixture for mocking Stripe in pytest
@pytest.fixture
def mock_stripe(monkeypatch):
    """Mock Stripe API calls for unit tests."""
    mock_customer = MagicMock()
    mock_customer.id = "cus_test123"
    monkeypatch.setattr("stripe.Customer.create", MagicMock(return_value=mock_customer))
    return mock_customer
```

## Security Checklist

- [ ] Webhook signature verification on ALL Stripe webhook endpoints
- [ ] Idempotency keys on ALL mutating Stripe API calls
- [ ] No PCI data (card numbers, CVV) stored in Cloud SQL
- [ ] Restricted API Keys (`rk_*`) used instead of root secret keys (`sk_*`)
- [ ] Test mode keys (`sk_test_` / `rk_test_`) in dev/staging, live keys in production only
- [ ] Connect onboarding uses Express (not Custom) accounts
- [ ] All amounts in cents (integer), never floating point dollars
- [ ] MCP `--tools` flag restricts to only the tools each service needs

## Reference Files

**Subscription setup and pricing**: See `reference/stripe-subscriptions.md` (when populated) for product/price creation, checkout session flow, subscription lifecycle, dunning configuration, and plan migration patterns. Until then, query the `stripe` MCP `search_stripe_documentation` tool.

**Stripe Connect and vendor payouts**: See `reference/stripe-connect.md` (when populated) for Express account onboarding, transfer creation, payout scheduling, and platform fee configuration. Until then, query the `stripe` MCP `search_stripe_documentation` tool.

## Process

1. **Query Stripe MCP** for current API signatures before writing any Stripe code — use `search_stripe_documentation` tool for API questions
2. **Webhook handler first** — implement the webhook before the API call that triggers it
3. **Idempotency keys** on every mutating call
4. **Test with Stripe CLI** — `stripe listen --forward-to` for local development
5. **Never bypass PCI compliance** — use Payment Sheet / Checkout, never raw card collection
6. **Use Restricted API Keys** — scope permissions to minimum required per service
