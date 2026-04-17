# TDD Patterns — Python 3.14 / FastAPI

## Test Structure (pytest + httpx)

```python
# tests/unit/test_user_service.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.user_service import UserService
from app.exceptions import ConflictError


@pytest.fixture
def user_service(mock_user_repository):
    return UserService(repository=mock_user_repository)


@pytest.fixture
def mock_user_repository():
    repo = AsyncMock()
    repo.find_by_email.return_value = None  # default: user not found
    return repo


class TestUserService:
    async def test_create_user_with_duplicate_email_raises_conflict(
        self, user_service, mock_user_repository
    ):
        # ARRANGE
        mock_user_repository.find_by_email.return_value = existing_user()

        # ACT + ASSERT
        with pytest.raises(ConflictError, match="Email already exists"):
            await user_service.create_user(new_user_dto())
```

## Integration Test (httpx AsyncClient)

```python
# tests/integration/test_users_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.anyio
async def test_post_users_valid_request_returns_201():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/users",
            json={"email": "test@example.com", "name": "Test User"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["email"] == "test@example.com"
```

## conftest.py Setup

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

## pyproject.toml Configuration

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.pytest.ini_options.markers]
unit = "Unit tests"
integration = "Integration tests"
```

## Mocking Rules

- `AsyncMock` for async functions/methods
- `MagicMock` for sync functions
- Use `pytest.fixture` for reusable mock setup
- Patch at the point of use: `patch("app.services.user_service.send_email")`
- Never patch builtins (`open`, `print`) unless absolutely necessary

## RED-GREEN Example

```bash
# RED
uv run pytest tests/unit/test_user_service.py::TestUserService::test_create_user_with_duplicate_email_raises_conflict -v
# Expected: FAILED

# GREEN — implement logic
uv run pytest tests/unit/test_user_service.py::TestUserService::test_create_user_with_duplicate_email_raises_conflict -v
# Expected: PASSED

# Full suite
uv run pytest
```
