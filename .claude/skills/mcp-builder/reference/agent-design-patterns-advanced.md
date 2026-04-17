# MCP Design Patterns for Autonomous Agents — Advanced

This reference covers patterns 6-10 plus domain-specific presets and tool design guidelines. For core patterns 1-5, read `agent-design-patterns.md`.

---

## Pattern 6: Idempotency & Safe Retry

**Problem**: Agent retries failed requests, creating duplicate orders/payments.

**Solution**: Use idempotency keys and return whether operation was already processed.

### TypeScript Interface

```typescript
interface IdempotentResponse<T> {
  idempotency_key: string;
  already_processed: boolean;
  original_result?: T;         // Result from first execution
  current_result: T;           // Same as original_result if already_processed
  message: string;
}
```

### Example JSON Output (First Call)

```json
{
  "idempotency_key": "create_order_usr123_20260202_143022",
  "already_processed": false,
  "original_result": null,
  "current_result": {
    "order_id": "ord_789",
    "status": "created",
    "total": 129.99
  },
  "message": "Order created successfully"
}
```

### Example JSON Output (Retry)

```json
{
  "idempotency_key": "create_order_usr123_20260202_143022",
  "already_processed": true,
  "original_result": {
    "order_id": "ord_789",
    "status": "created",
    "total": 129.99
  },
  "current_result": {
    "order_id": "ord_789",
    "status": "created",
    "total": 129.99
  },
  "message": "Order was already created with this idempotency key. Returning original result."
}
```

---

## Pattern 7: Context Carryover

**Problem**: Agent loses context between tool calls in multi-step workflows.

**Solution**: Include session/conversation IDs and structured context to carry forward.

### TypeScript Interface

```typescript
interface ContextAwareResponse<T> {
  data: T;
  session_id?: string;
  conversation_id?: string;
  carry_forward: Record<string, unknown>;  // Context for next tool call
  next_tool_hint?: string;
}
```

### Example JSON Output

```json
{
  "data": {
    "items_in_cart": 3,
    "cart_total": 87.50
  },
  "session_id": "sess_abc123",
  "conversation_id": "conv_xyz789",
  "carry_forward": {
    "cart_id": "cart_456",
    "user_id": "usr_123",
    "selected_shipping": "express",
    "payment_method_id": "pm_card_end_4242",
    "workflow_step": "review_before_checkout"
  },
  "next_tool_hint": "checkout_cart"
}
```

---

## Pattern 8: Capability Advertisement

**Problem**: Agent tries to use tool beyond its capabilities (file size, formats, rate limits).

**Solution**: Tools advertise capabilities, limits, and cost estimates upfront.

### TypeScript Interface

```typescript
interface CapabilityResponse {
  tool: string;
  capabilities: string[];
  max_file_size_mb?: number;
  supported_operations: string[];
  limitations: string[];
  cost_estimate?: {
    credits_per_call?: number;
    rate_limit?: string;
  };
}
```

### Example JSON Output

```json
{
  "tool": "image_analysis",
  "capabilities": [
    "object_detection",
    "ocr",
    "face_detection",
    "image_classification"
  ],
  "max_file_size_mb": 10,
  "supported_operations": [
    "analyze_image",
    "extract_text",
    "detect_faces"
  ],
  "limitations": [
    "PNG, JPEG, WebP only",
    "Max resolution: 4096x4096",
    "No video support",
    "OCR limited to English, Spanish, French"
  ],
  "cost_estimate": {
    "credits_per_call": 5,
    "rate_limit": "100 requests/hour"
  }
}
```

---

## Pattern 9: Circuit Breaker Status

**Problem**: Agent repeatedly calls a failing external service, wasting time and resources.

**Solution**: Tools expose circuit breaker state and recommend fallback actions.

### TypeScript Interface

```typescript
interface CircuitBreakerStatus {
  service: string;
  circuit_state: "closed" | "open" | "half_open";
  failure_rate: number;            // 0.0 - 1.0
  last_success?: string;           // ISO 8601 timestamp
  recommendation: string;
  fallback_tool?: string;
  expected_recovery?: string;      // ISO 8601 timestamp
}
```

### Example JSON Output (Circuit Open)

```json
{
  "service": "payment_gateway",
  "circuit_state": "open",
  "failure_rate": 0.95,
  "last_success": "2026-02-02T14:22:00Z",
  "recommendation": "Use fallback payment processor or retry after 15 minutes",
  "fallback_tool": "fallback_payment_processor",
  "expected_recovery": "2026-02-02T14:45:00Z"
}
```

### Example JSON Output (Circuit Closed)

```json
{
  "service": "payment_gateway",
  "circuit_state": "closed",
  "failure_rate": 0.02,
  "last_success": "2026-02-02T14:30:00Z",
  "recommendation": "Service healthy - proceed normally",
  "fallback_tool": null,
  "expected_recovery": null
}
```

---

## Pattern 10: Audit Trail

**Problem**: Cannot debug agent decisions or trace data sources in production.

**Solution**: Include correlation ID, tool chain, data sources, and metadata in every response.

### TypeScript Interface

```typescript
interface AuditedResponse<T> {
  data: T;
  correlation_id: string;          // Unique ID for this request chain
  tool_chain: string[];            // Sequence of tools called
  data_sources: string[];          // APIs, DBs, files accessed
  timestamp: string;               // ISO 8601
  model_version?: string;          // If using ML models
  human_reviewable: boolean;       // Flag for compliance review
}
```

### Example JSON Output

```json
{
  "data": {
    "fraud_risk_score": 0.82,
    "recommendation": "block_transaction"
  },
  "correlation_id": "req_20260202_143045_abc123",
  "tool_chain": [
    "get_user",
    "get_transaction_history",
    "analyze_fraud_risk"
  ],
  "data_sources": [
    "postgres://users_db",
    "https://api.frauddetection.example.com/v2/analyze",
    "redis://cache_cluster"
  ],
  "timestamp": "2026-02-02T14:30:45Z",
  "model_version": "fraud-detector-v2.3.1",
  "human_reviewable": true
}
```

---
