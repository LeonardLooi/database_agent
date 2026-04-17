# FastAPI Error Handling Patterns

Production-ready error handling for Python 3.14 + FastAPI. All retry and circuit breaker
patterns are async-safe — no `time.sleep()` in async routes.

> **Workspace rule:** NO silent failures, NO fallbacks, NO mock data on error.
> Every catch block MUST log AND either rethrow or return an explicit error state.
> See `code-standards.md §Error Handling`.

---

## Dependencies

```bash
uv add tenacity circuitbreaker
```

```toml
# pyproject.toml
[project]
dependencies = [
    "tenacity>=9.0.0",
    "circuitbreaker>=2.0.0",
]
```

---

## 1. Custom Exception Hierarchy

Domain-layer exceptions — HTTP translation happens at the FastAPI boundary only.
Services raise typed domain exceptions; never raise `HTTPException` inside services.

```python
# src/my_service/core/exceptions.py
from __future__ import annotations
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base exception for all application domain errors."""

    def __init__(self, message: str, code: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={str(self)!r})"


class ValidationError(AppError):
    """Input failed business-rule validation (distinct from Pydantic schema validation)."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR", details={"field": field} if field else {})


class NotFoundError(AppError):
    """Requested resource does not exist."""

    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            f"{resource} not found",
            code="NOT_FOUND",
            details={"resource": resource, "id": identifier},
        )


class ConflictError(AppError):
    """Operation conflicts with current resource state (e.g. duplicate)."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, code="CONFLICT", details=details)


class ExternalServiceError(AppError):
    """Dependency (external API, payment gateway, etc.) failed."""

    def __init__(self, message: str, service: str, details: dict | None = None) -> None:
        super().__init__(message, code="EXTERNAL_SERVICE_ERROR", details={"service": service, **(details or {})})
        self.service = service
```

---

## 2. FastAPI Exception Handlers

Register once in `main.py`. Translates domain exceptions to HTTP responses.
Never catch `AppError` subclasses inside route handlers — let the handler do it.

```python
# src/my_service/core/exception_handlers.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .exceptions import AppError, ValidationError, NotFoundError, ConflictError, ExternalServiceError
import logging

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        logger.info("Resource not found: %s", exc, extra={"code": exc.code, "details": exc.details})
        return JSONResponse(status_code=404, content={"code": exc.code, "detail": str(exc), "details": exc.details})

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        logger.info("Validation error: %s", exc, extra={"code": exc.code, "details": exc.details})
        return JSONResponse(status_code=422, content={"code": exc.code, "detail": str(exc), "details": exc.details})

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        logger.warning("Conflict: %s", exc, extra={"code": exc.code, "details": exc.details})
        return JSONResponse(status_code=409, content={"code": exc.code, "detail": str(exc), "details": exc.details})

    @app.exception_handler(ExternalServiceError)
    async def external_service_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
        logger.error("External service failed: %s | service=%s", exc, exc.service, extra=exc.details)
        return JSONResponse(status_code=502, content={"code": exc.code, "detail": str(exc)})

    @app.exception_handler(AppError)
    async def app_error_fallback_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.error("Unclassified application error: %r", exc, extra={"code": exc.code})
        return JSONResponse(status_code=500, content={"code": exc.code, "detail": str(exc)})
```

Register in `main.py`:

```python
# src/my_service/main.py
from .core.exception_handlers import register_exception_handlers

app = FastAPI(...)
register_exception_handlers(app)
```

---

## 3. Service Layer — Using Domain Exceptions

Services raise typed exceptions. Never raise `HTTPException` here.

```python
# src/my_service/services/order_service.py
import logging
from sqlalchemy.exc import IntegrityError
from .core.exceptions import NotFoundError, ConflictError, ExternalServiceError

logger = logging.getLogger(__name__)


async def get_order(order_id: str, session: AsyncSession) -> Order:
    order = await session.get(Order, order_id)
    if not order:
        raise NotFoundError("Order", order_id)
    return order


async def create_order(data: CreateOrderRequest, session: AsyncSession) -> Order:
    try:
        order = Order(**data.model_dump())
        session.add(order)
        await session.commit()
        return order
    except IntegrityError as exc:
        await session.rollback()
        logger.error("Duplicate order creation attempt: %s", exc)
        raise ConflictError("Order already exists", details={"reference": data.reference}) from exc


async def charge_order(order: Order) -> PaymentResult:
    try:
        return await payment_client.charge(order.total)
    except PaymentClientError as exc:
        logger.error("Payment failed for order %s: %s", order.id, exc)
        raise ExternalServiceError(
            "Payment processing failed",
            service="payment_service",
            details={"order_id": str(order.id), "amount": str(order.total)},
        ) from exc
```

---

## 4. Async Retry with Tenacity

Use `tenacity` — it is async-safe. **Never use `time.sleep()` inside async routes.**

```python
# src/my_service/core/retry.py
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

logger = logging.getLogger(__name__)

# Decorator — use on any async function that calls external APIs
def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_on: tuple = (ExternalServiceError,),
):
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retry_on),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,  # MUST rethrow after max attempts — no silent fallback
    )
```

Usage:

```python
from .core.retry import with_retry
from .core.exceptions import ExternalServiceError

@with_retry(max_attempts=3, retry_on=(ExternalServiceError,))
async def fetch_exchange_rate(currency: str) -> float:
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"https://api.rates.io/{currency}")
            resp.raise_for_status()
            return resp.json()["rate"]
        except httpx.HTTPError as exc:
            logger.error("Exchange rate fetch failed for %s: %s", currency, exc)
            raise ExternalServiceError(
                f"Rate service unavailable for {currency}",
                service="exchange_rate_api",
            ) from exc
```

---

## 5. Async Circuit Breaker

Prevents cascading failures when an external service is down.

```python
# src/my_service/core/circuit.py
from circuitbreaker import circuit
from .exceptions import ExternalServiceError

# failure_threshold: open after N consecutive failures
# recovery_timeout: seconds before allowing one test call (HALF_OPEN)
# expected_exception: only these exceptions count as failures

def breaker(service_name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
    """Factory returning a circuit breaker decorator for a named external service."""
    return circuit(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=ExternalServiceError,
        name=service_name,
    )
```

Usage:

```python
from .core.circuit import breaker
from .core.retry import with_retry

@breaker("payment_service", failure_threshold=5, recovery_timeout=60)
@with_retry(max_attempts=3)
async def call_payment_service(order_id: str, amount: Decimal) -> PaymentResult:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post("/charge", json={"order_id": order_id, "amount": str(amount)})
            resp.raise_for_status()
            return PaymentResult(**resp.json())
        except httpx.HTTPError as exc:
            logger.error("Payment service call failed: %s", exc)
            raise ExternalServiceError("Payment service unavailable", service="payment_service") from exc
```

> **Circuit open state:** When circuit opens, `circuitbreaker` raises `CircuitBreakerError`.
> Add a handler for it in `exception_handlers.py` returning `503 Service Unavailable`.

```python
# Add to register_exception_handlers()
from circuitbreaker import CircuitBreakerError

@app.exception_handler(CircuitBreakerError)
async def circuit_open_handler(request: Request, exc: CircuitBreakerError) -> JSONResponse:
    logger.error("Circuit breaker open: %s", exc)
    return JSONResponse(status_code=503, content={"code": "SERVICE_UNAVAILABLE", "detail": str(exc)})
```

---

## 6. Error Logging Context Pattern

Structured logging with request context — include user, path, method in every error log.

```python
# src/my_service/middleware/logging_middleware.py
import logging
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(
                "Unhandled exception: %s %s — %r",
                request.method,
                request.url.path,
                exc,
                extra={"request_id": request_id},
            )
            raise
```

Register in `main.py`:
```python
from .middleware.logging_middleware import RequestContextMiddleware
app.add_middleware(RequestContextMiddleware)
```

---

## 7. Error Handling Rules

| Rule | Detail |
|------|--------|
| **Never raise `HTTPException` in services** | Services use domain exceptions; HTTP translation is the handler's job |
| **Never swallow exceptions** | Every `except` MUST log AND rethrow or raise domain error |
| **No fallbacks** | Returning empty list/None/default on error is forbidden (`code-standards.md`) |
| **Chain exceptions** | Use `raise NewError(...) from original_exc` to preserve traceback |
| **Async-safe retry** | Use `tenacity` — never `time.sleep()` in async routes |
| **Circuit breaker on external services** | Wrap all third-party HTTP clients |
| **Log at correct level** | 4xx expected errors → `INFO`/`WARNING`; 5xx → `ERROR` |
| **Never log sensitive data** | No passwords, tokens, PII in error details |

---

## 8. Testing Error Paths

```python
# tests/test_error_handling.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from src.my_service.main import app
from src.my_service.core.exceptions import NotFoundError, ExternalServiceError

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_not_found_returns_404(client):
    resp = await client.get("/api/v1/orders/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"

@pytest.mark.asyncio
async def test_external_service_failure_returns_502(client, seed_order):
    with patch("src.my_service.services.order_service.payment_client.charge",
               new_callable=AsyncMock) as mock_charge:
        mock_charge.side_effect = ExternalServiceError("down", service="payment_service")
        resp = await client.post(f"/api/v1/orders/{seed_order.id}/charge")
    assert resp.status_code == 502
    assert resp.json()["code"] == "EXTERNAL_SERVICE_ERROR"

@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failure(client):
    call_count = 0

    async def flaky_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ExternalServiceError("transient", service="test")
        return {"rate": 1.5}

    with patch("src.my_service.services.exchange_service.fetch_exchange_rate", side_effect=flaky_call):
        resp = await client.get("/api/v1/exchange/USD")
    assert resp.status_code == 200
    assert call_count == 3  # confirmed: retried twice, succeeded on third

@pytest.mark.asyncio
async def test_domain_exception_never_leaks_as_500(client):
    """NotFoundError must produce 404, not 500 — verify handler is registered."""
    with patch("src.my_service.services.order_service.get_order",
               side_effect=NotFoundError("Order", "abc")):
        resp = await client.get("/api/v1/orders/abc")
    assert resp.status_code == 404
    assert "INTERNAL" not in resp.json().get("code", "")
```
