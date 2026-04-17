# Inbound Rate Limiting — FastAPI

## SlowAPI (recommended for simple route limits)

SlowAPI wraps `limits` and integrates with FastAPI/Starlette.

Install:

```bash
pip install slowapi
```

Setup in `main.py`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

Per-route usage:

```python
@app.post("/api/v1/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    ...

@app.post("/api/v1/auth/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    ...

@app.get("/api/v1/items")
@limiter.limit("200/minute")
async def list_items(request: Request):
    ...
```

## Production: Redis Backend

For multi-instance deployments (Cloud Run), use Redis storage:

```python
from slowapi import Limiter
from limits.storage import RedisStorage

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://redis-host:6379",
)
```

## GCP Cloud Armor (Edge)

Same Cloud Armor policy as other stacks — configure on GCP Load Balancer:
- 100 req/min per IP baseline
- Tighter limits on auth endpoints
- OWASP CRS enabled

See `java-spring-api/reference/spring-boot-rate-limiting.md` for Terraform example.

## Auth Endpoint Limits

- Login: 5/minute per IP
- Password reset: 3/hour per email
- Register: 3/hour per IP
