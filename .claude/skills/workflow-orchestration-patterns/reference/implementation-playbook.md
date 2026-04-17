# Workflow Orchestration Implementation Playbook

> Referenced by `SKILL.md`. Load when implementing Temporal workflows in Java, Python, or NestJS.

## SDK Setup Per Stack

### Java 21 / Spring Boot 3.5.x

pom.xml dependencies:
```xml
<dependency>
    <groupId>io.temporal</groupId>
    <artifactId>temporal-sdk</artifactId>
    <version>1.25.0</version>
</dependency>
<dependency>
    <groupId>io.temporal</groupId>
    <artifactId>temporal-spring-boot-autoconfigure-alpha</artifactId>
    <version>0.6.0</version>
</dependency>
```

application.yml:
```yaml
spring:
  temporal:
    connection:
      target: 127.0.0.1:7233
    workers:
      - task-queue: order-processing
        workflow-classes:
          - com.example.workflows.OrderWorkflow
        activity-beans:
          - paymentActivity
          - inventoryActivity
          - notificationActivity
```

### Python 3.14 / FastAPI

pyproject.toml:
```toml
[project]
dependencies = [
    "temporalio==1.7.0",
    "fastapi>=0.135.2",
    "uvicorn[standard]",
    "pydantic>=2.0",
]
```

Worker startup (separate process from FastAPI):
```python
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from .workflows import OrderWorkflow
from .activities import PaymentActivities, InventoryActivities

async def run_worker():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="order-processing",
        workflows=[OrderWorkflow],
        activities=[
            PaymentActivities.charge_payment,
            PaymentActivities.refund_payment,
            InventoryActivities.reserve_inventory,
            InventoryActivities.release_inventory,
        ],
    ):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(run_worker())
```

### NestJS 11.x / TypeScript

```typescript
// worker.ts — run as separate process
import { NativeConnection, Worker } from '@temporalio/worker';
import * as activities from './activities';

async function runWorker() {
  const connection = await NativeConnection.connect({ address: 'localhost:7233' });
  const worker = await Worker.create({
    connection,
    namespace: 'default',
    taskQueue: 'order-processing',
    workflowsPath: require.resolve('./workflows'),
    activities,
  });
  await worker.run();
}

runWorker().catch((err) => {
  console.error(err);
  process.exit(1);
});
```

---

## Saga Pattern with Compensation {#saga}

### Python — Saga Workflow

```python
from dataclasses import dataclass
from datetime import timedelta
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

@dataclass
class OrderInput:
    order_id: str
    user_id: str
    amount_cents: int
    product_id: str

@workflow.defn
class OrderSagaWorkflow:
    @workflow.run
    async def run(self, input: OrderInput) -> str:
        compensations: list = []

        try:
            # Step 1: Reserve inventory
            await workflow.execute_activity(
                reserve_inventory,
                args=[input.order_id, input.product_id],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            compensations.append(("release_inventory", [input.order_id, input.product_id]))

            # Step 2: Charge payment
            await workflow.execute_activity(
                charge_payment,
                args=[input.order_id, input.user_id, input.amount_cents],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    non_retryable_error_types=["InsufficientFundsError", "InvalidCardError"],
                ),
            )
            compensations.append(("refund_payment", [input.order_id, input.amount_cents]))

            # Step 3: Fulfill order
            await workflow.execute_activity(
                fulfill_order,
                args=[input.order_id],
                start_to_close_timeout=timedelta(minutes=5),
            )

            return f"Order {input.order_id} fulfilled"

        except ActivityError as e:
            # Run compensations in reverse order (LIFO)
            for comp_name, comp_args in reversed(compensations):
                try:
                    await workflow.execute_activity(
                        comp_name,
                        args=comp_args,
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=RetryPolicy(maximum_attempts=5),
                    )
                except Exception:
                    # Log but continue — best-effort compensation
                    pass
            raise ApplicationError(f"Order {input.order_id} failed, compensated") from e
```

### Java — Saga Workflow

```java
@WorkflowInterface
public interface OrderWorkflow {
    @WorkflowMethod
    String processOrder(OrderInput input);
}

@WorkflowImpl
public class OrderWorkflowImpl implements OrderWorkflow {

    private final PaymentActivities payment = Workflow.newActivityStub(
        PaymentActivities.class,
        ActivityOptions.newBuilder()
            .setStartToCloseTimeout(Duration.ofSeconds(30))
            .setRetryOptions(RetryOptions.newBuilder()
                .setMaximumAttempts(3)
                .setDoNotRetry("InsufficientFundsError", "InvalidCardError")
                .build())
            .build()
    );

    private final InventoryActivities inventory = Workflow.newActivityStub(
        InventoryActivities.class,
        ActivityOptions.newBuilder()
            .setStartToCloseTimeout(Duration.ofSeconds(30))
            .build()
    );

    @Override
    public String processOrder(OrderInput input) {
        Saga saga = new Saga(new Saga.Options.Builder().setParallelCompensation(false).build());

        try {
            inventory.reserveInventory(input.getOrderId(), input.getProductId());
            saga.addCompensation(inventory::releaseInventory, input.getOrderId(), input.getProductId());

            payment.chargePayment(input.getOrderId(), input.getUserId(), input.getAmountCents());
            saga.addCompensation(payment::refundPayment, input.getOrderId(), input.getAmountCents());

            return "Order " + input.getOrderId() + " fulfilled";

        } catch (ActivityFailure e) {
            saga.compensate();
            throw e;
        }
    }
}
```

### NestJS — Saga Workflow

```typescript
// workflows/order-saga.workflow.ts
import { proxyActivities, ApplicationFailure } from '@temporalio/workflow';
import type * as activities from '../activities';
import { OrderInput } from '../types';

const { reserveInventory, releaseInventory, chargePayment, refundPayment, fulfillOrder } =
  proxyActivities<typeof activities>({
    startToCloseTimeout: '30 seconds',
    retry: { maximumAttempts: 3 },
  });

export async function orderSagaWorkflow(input: OrderInput): Promise<string> {
  const compensations: Array<() => Promise<void>> = [];

  try {
    await reserveInventory(input.orderId, input.productId);
    compensations.push(() => releaseInventory(input.orderId, input.productId));

    await chargePayment(input.orderId, input.userId, input.amountCents);
    compensations.push(() => refundPayment(input.orderId, input.amountCents));

    await fulfillOrder(input.orderId);
    return `Order ${input.orderId} fulfilled`;

  } catch (err) {
    // Run compensations in reverse order (LIFO)
    for (const compensate of compensations.reverse()) {
      try {
        await compensate();
      } catch {
        // best-effort compensation — log and continue
      }
    }
    throw ApplicationFailure.create({ message: `Order ${input.orderId} failed, compensated` });
  }
}
```

---

## Entity Workflow (Actor Model) {#entity}

One workflow execution = one entity. Receives signals for mutations, handles queries for reads.

### Python — Shopping Cart Entity Workflow

```python
from dataclasses import dataclass, field
from datetime import timedelta
from temporalio import workflow

@dataclass
class CartItem:
    product_id: str
    quantity: int
    price_cents: int

@workflow.defn
class ShoppingCartWorkflow:
    def __init__(self) -> None:
        self._items: list[CartItem] = []
        self._checked_out: bool = False

    @workflow.run
    async def run(self, cart_id: str) -> str:
        # Cart expires after 24 hours of inactivity
        await workflow.wait_condition(
            lambda: self._checked_out,
            timeout=timedelta(hours=24),
        )
        if self._checked_out:
            return f"Cart {cart_id} checked out with {len(self._items)} items"
        return f"Cart {cart_id} expired"

    @workflow.signal
    async def add_item(self, item: CartItem) -> None:
        self._items.append(item)

    @workflow.signal
    async def remove_item(self, product_id: str) -> None:
        self._items = [i for i in self._items if i.product_id != product_id]

    @workflow.signal
    async def checkout(self) -> None:
        self._checked_out = True

    @workflow.query
    def get_items(self) -> list[CartItem]:
        return self._items

    @workflow.query
    def total_cents(self) -> int:
        return sum(i.price_cents * i.quantity for i in self._items)
```

### Java — Shopping Cart Entity Workflow

```java
@WorkflowInterface
public interface ShoppingCartWorkflow {
    @WorkflowMethod
    String run(String cartId);

    @SignalMethod
    void addItem(CartItem item);

    @SignalMethod
    void removeItem(String productId);

    @SignalMethod
    void checkout();

    @QueryMethod
    List<CartItem> getItems();

    @QueryMethod
    int getTotalCents();
}

@WorkflowImpl
public class ShoppingCartWorkflowImpl implements ShoppingCartWorkflow {
    private final List<CartItem> items = new ArrayList<>();
    private boolean checkedOut = false;

    @Override
    public String run(String cartId) {
        Workflow.await(Duration.ofHours(24), () -> checkedOut);
        return checkedOut
            ? "Cart " + cartId + " checked out"
            : "Cart " + cartId + " expired";
    }

    @Override public void addItem(CartItem item) { items.add(item); }
    @Override public void removeItem(String productId) { items.removeIf(i -> i.getProductId().equals(productId)); }
    @Override public void checkout() { checkedOut = true; }
    @Override public List<CartItem> getItems() { return Collections.unmodifiableList(items); }
    @Override public int getTotalCents() { return items.stream().mapToInt(i -> i.getPriceCents() * i.getQuantity()).sum(); }
}
```

---

## Fan-Out / Fan-In {#fanout}

Execute N tasks in parallel, aggregate results.

### Python — Parallel Document Processing

```python
import asyncio
from temporalio import workflow
from temporalio.workflow import ParentClosePolicy

@workflow.defn
class DocumentBatchWorkflow:
    @workflow.run
    async def run(self, document_ids: list[str]) -> dict[str, str]:
        # Fan-out: start all child workflows in parallel
        handles = [
            await workflow.start_child_workflow(
                ProcessDocumentWorkflow,
                args=[doc_id],
                id=f"process-doc-{doc_id}",
                parent_close_policy=ParentClosePolicy.TERMINATE,
            )
            for doc_id in document_ids
        ]

        # Fan-in: wait for all and collect results
        results = await asyncio.gather(*[h.result() for h in handles])
        return dict(zip(document_ids, results))
```

**Scaling rule:** Do not put 1M tasks in one workflow. Decompose: 1M tasks = 1K child workflows x 1K tasks each.

---

## Signals and Async Callbacks {#signals}

### Python — Human Approval Workflow

```python
from temporalio import workflow
from datetime import timedelta

@workflow.defn
class ApprovalWorkflow:
    def __init__(self) -> None:
        self._approved: bool | None = None

    @workflow.run
    async def run(self, request_id: str, timeout_hours: int = 48) -> str:
        # Wait for approval signal with timeout
        approved = await workflow.wait_condition(
            lambda: self._approved is not None,
            timeout=timedelta(hours=timeout_hours),
        )
        if not approved:
            return f"Request {request_id} timed out — auto-rejected"
        return f"Request {request_id} {'approved' if self._approved else 'rejected'}"

    @workflow.signal
    async def approve(self) -> None:
        self._approved = True

    @workflow.signal
    async def reject(self) -> None:
        self._approved = False
```

---

## Activity Heartbeats {#heartbeat}

For activities running longer than 30 seconds.

### Python — Long-Running File Processing Activity

```python
from temporalio import activity
from datetime import timedelta

@activity.defn
async def process_large_file(file_path: str, chunk_size_mb: int = 10) -> str:
    """Process a large file in chunks with heartbeat reporting."""
    chunks = get_file_chunks(file_path, chunk_size_mb)
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        # Heartbeat every chunk — includes progress for resume after failure
        activity.heartbeat(f"Processing chunk {i+1}/{total}")
        await process_chunk(chunk)

    return f"Processed {total} chunks from {file_path}"
```

Activity options for heartbeat:
```python
ActivityOptions(
    start_to_close_timeout=timedelta(hours=2),
    heartbeat_timeout=timedelta(seconds=30),  # fails if no heartbeat in 30s
)
```

### Java — Long-Running Activity with Heartbeat

```java
@ActivityImpl
public class FileProcessingActivitiesImpl implements FileProcessingActivities {

    @Override
    public String processLargeFile(String filePath) {
        List<FileChunk> chunks = getFileChunks(filePath);
        for (int i = 0; i < chunks.size(); i++) {
            Activity.getExecutionContext().heartbeat("Chunk " + (i + 1) + "/" + chunks.size());
            processChunk(chunks.get(i));
        }
        return "Processed " + chunks.size() + " chunks";
    }
}
```

---

## Workflow Versioning {#versioning}

Safe changes to workflow code while old executions are still running.

### Python

```python
@workflow.defn
class OrderWorkflow:
    @workflow.run
    async def run(self, input: OrderInput) -> str:
        # Use patched() to branch behavior for new vs old executions
        if workflow.patched("add-notification-step"):
            # New code path for executions started after this deploy
            await workflow.execute_activity(send_notification, args=[input.order_id], ...)

        await workflow.execute_activity(fulfill_order, args=[input.order_id], ...)
        return "done"
```

### Java

```java
@Override
public String processOrder(OrderInput input) {
    int version = Workflow.getVersion("add-notification-step", Workflow.DEFAULT_VERSION, 1);
    if (version == 1) {
        notification.sendNotification(input.getOrderId());
    }
    // ... rest of workflow
}
```

---

## Child Workflows {#child}

Decompose large workflows for scalability and isolation.

### Python — Parent Dispatching Child Workflows

```python
from temporalio import workflow
from temporalio.workflow import ParentClosePolicy

@workflow.defn
class BulkNotificationWorkflow:
    @workflow.run
    async def run(self, user_ids: list[str], message: str) -> dict[str, str]:
        # Decompose into batches of 1000 to stay under history limits
        batch_size = 1000
        batches = [user_ids[i:i + batch_size] for i in range(0, len(user_ids), batch_size)]

        handles = [
            await workflow.start_child_workflow(
                NotificationBatchWorkflow,
                args=[batch, message],
                id=f"notify-batch-{idx}",
                parent_close_policy=ParentClosePolicy.TERMINATE,
            )
            for idx, batch in enumerate(batches)
        ]

        results = await asyncio.gather(*[h.result() for h in handles])
        return {"total_batches": len(batches), "results": results}
```

---

## Retry Policies {#retry}

### Non-Retryable Error Classification

**Python:**
```python
# In activity: throw non-retryable for business rule violations
from temporalio.exceptions import ApplicationError

async def charge_payment(order_id: str, amount_cents: int) -> None:
    result = await payment_gateway.charge(order_id, amount_cents)
    if result.code == "INSUFFICIENT_FUNDS":
        raise ApplicationError(
            "Payment declined — insufficient funds",
            "InsufficientFundsError",
            non_retryable=True,  # do not retry
        )
    if result.code == "NETWORK_TIMEOUT":
        raise ApplicationError("Gateway timeout", "NetworkTimeoutError")  # retryable (default)
```

**Java:**
```java
// Non-retryable: throw ApplicationFailure
throw ApplicationFailure.newNonRetryableFailure("Insufficient funds", "InsufficientFundsError");

// Retryable (default behavior — just throw any other exception):
throw new RuntimeException("Gateway timeout");
```

**NestJS:**
```typescript
import { ApplicationFailure } from '@temporalio/workflow';

// In activity:
throw ApplicationFailure.create({
  message: 'Payment declined',
  type: 'InsufficientFundsError',
  nonRetryable: true,
});
```

### Standard Retry Policy

```python
# Python
RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=5,
    non_retryable_error_types=["InsufficientFundsError", "ValidationError"],
)
```

```java
// Java
RetryOptions.newBuilder()
    .setInitialInterval(Duration.ofSeconds(1))
    .setBackoffCoefficient(2.0)
    .setMaximumInterval(Duration.ofSeconds(60))
    .setMaximumAttempts(5)
    .setDoNotRetry("InsufficientFundsError", "ValidationError")
    .build()
```

---

## Starting Workflows (Client Code)

### Python — FastAPI Client

```python
from temporalio.client import Client
from fastapi import FastAPI
from .workflows import OrderSagaWorkflow
from .types import OrderInput

from contextlib import asynccontextmanager

temporal_client: Client | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global temporal_client
    temporal_client = await Client.connect("localhost:7233")
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/orders")
async def create_order(input: OrderInput):
    handle = await temporal_client.start_workflow(
        OrderSagaWorkflow.run,
        input,
        id=f"order-{input.order_id}",
        task_queue="order-processing",
    )
    return {"workflow_id": handle.id, "run_id": handle.first_execution_run_id}
```

### Java — Spring Boot REST Controller

```java
@RestController
@RequestMapping("/orders")
@RequiredArgsConstructor
public class OrderController {

    private final WorkflowClient workflowClient;

    @PostMapping
    public ResponseEntity<OrderResponse> createOrder(@RequestBody @Valid OrderInput input) {
        OrderWorkflow workflow = workflowClient.newWorkflowStub(
            OrderWorkflow.class,
            WorkflowOptions.newBuilder()
                .setWorkflowId("order-" + input.getOrderId())
                .setTaskQueue("order-processing")
                .build()
        );

        WorkflowClient.start(workflow::processOrder, input);
        return ResponseEntity.accepted().body(new OrderResponse(input.getOrderId()));
    }
}
```

### NestJS — Controller + Temporal Client Service

```typescript
// temporal-client.service.ts
import { Injectable, OnModuleInit } from '@nestjs/common';
import { Client, Connection } from '@temporalio/client';
import { orderSagaWorkflow } from './workflows/order-saga.workflow';
import { OrderInput } from './types';

@Injectable()
export class TemporalClientService implements OnModuleInit {
  private client: Client;

  async onModuleInit() {
    const connection = await Connection.connect({ address: 'localhost:7233' });
    this.client = new Client({ connection });
  }

  async startOrderWorkflow(input: OrderInput): Promise<string> {
    const handle = await this.client.workflow.start(orderSagaWorkflow, {
      args: [input],
      taskQueue: 'order-processing',
      workflowId: `order-${input.orderId}`,
    });
    return handle.workflowId;
  }
}
```

---

## Common Pitfalls

| Mistake | Why It Breaks | Fix |
|---------|--------------|-----|
| `datetime.now()` in workflow | Non-deterministic — replay produces different time | Use `workflow.now()` |
| HTTP call in workflow | Non-deterministic, may fail | Move to activity |
| Non-idempotent activity | Retries cause duplicate charges/sends | Add idempotency key or upsert |
| Missing heartbeat on long activity | Temporal can't detect stalled work | Call `heartbeat()` every <30s |
| No `non_retryable_error_types` | Validation errors retried forever | Classify errors explicitly |
| Giant workflow (1M tasks in one) | History size limit hit | Use child workflows to decompose |
| Changing workflow code without versioning | Old executions replay incorrectly | Use `workflow.patched()` / `Workflow.getVersion()` |
