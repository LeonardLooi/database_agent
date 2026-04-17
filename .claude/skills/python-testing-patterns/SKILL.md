---
name: python-testing-patterns
description: Comprehensive pytest patterns for Python 3.14 / FastAPI — fixtures, parametrize, mocking, async testing, database fixtures, test markers, coverage config, and CI integration. Use when writing or structuring Python test suites beyond the basic TDD cycle.
allowed-tools: Read, Write, Edit, Bash
metadata:
  triggers: pytest, pytest fixtures, parametrize, pytest mocking, async tests, test database, coverage config, pytest markers, Python test suite, conftest.py, GitHub Actions tests, property-based testing, Hypothesis pytest
  related-skills: test-driven-development, python-dev, agentic-ai-dev
  domain: quality
  role: specialist
  scope: testing
  output-format: code
last-reviewed: "2026-03-14"
---

## Iron Law

**NO TEST INFRASTRUCTURE WITHOUT READING THE PLAYBOOK FIRST — fixtures, markers, and coverage config have workspace-specific patterns that prevent test debt**

# Python Testing Patterns

Deep reference for pytest test infrastructure, fixtures, async patterns, and CI integration for Python 3.14 / FastAPI services.

## When to Use

Load this skill when:
- Setting up a new test suite from scratch (conftest.py, pyproject.toml config)
- Writing parametrized tests for multiple input scenarios
- Mocking async dependencies (AsyncMock patterns)
- Testing database operations with session fixtures
- Configuring test markers (`slow`, `integration`) for selective execution
- Setting up coverage reporting gates
- Wiring GitHub Actions CI for Python tests

Load `test-driven-development` skill first for the Red-Green-Refactor process. This skill handles the *infrastructure* — not the TDD process.

## Quick Reference

| Need | Pattern |
|------|---------|
| Multiple inputs | `@pytest.mark.parametrize` |
| Async test | `@pytest.mark.asyncio` + `AsyncMock` |
| HTTP endpoint test | `httpx.AsyncClient` + `ASGITransport` |
| DB session in test | `AsyncSession` fixture + rollback teardown |
| Slow/integration gate | `@pytest.mark.slow` + `-m "not slow"` in CI |
| Coverage gate | `pytest --cov=src --cov-fail-under=80` |
| Property-based | `@given(st.text())` from Hypothesis |

## Reference File

Load `resources/implementation-playbook.md` for:
- 10 fundamental patterns (fixtures, parametrize, mocking, async, monkeypatch, tmp_path, Hypothesis)
- 10 advanced patterns (DB fixtures, test markers, coverage config, CI workflow, test organization)
- Full conftest.py templates
- GitHub Actions workflow for Python tests
- pytest.ini / pyproject.toml configuration

## Relationship to Other Skills

- `test-driven-development` — process (Red-Green-Refactor, when to write tests, naming)
- `python-testing-patterns` — infrastructure (how to structure, configure, and run tests)
- `agentic-ai-dev/reference/agentic-testing.md` — LangGraph agent-specific testing patterns

## Post-Test Checklist

- [ ] `pytest -q` — all tests pass
- [ ] `pytest --cov=src --cov-report=term-missing` — coverage visible
- [ ] No `print()` in test files — use `capfd` fixture or logging
- [ ] Async tests use `@pytest.mark.asyncio` or `asyncio_mode = "auto"` in config
- [ ] External services mocked — no real HTTP calls in unit tests
