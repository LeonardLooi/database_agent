# Agentic AI Makefile Patterns

Makefile command reference for agentic AI services using `uv`, pytest, Docker Compose, and a full observability stack. Patterns sourced from weather-ai-agent-service. **Adapt command names and targets to your project — these are from the weather-ai-agent-service reference.**

## Quick Start (5 Most Important Commands)

```bash
make install-dev       # Install all dependencies (prod + dev) via uv
make verify            # Run automated setup verification (checks API keys, connectivity)
make docker-up-dev     # Start all services in development mode (hot reload)
make test-dev          # Restart dev env + run full test suite + compliance check
make all-checks        # Lint + type-check + test (run before every commit)
```

## uv Integration Pattern

This service uses `uv` for dependency management. The key distinction:

```makefile
install:      ## Install production dependencies only
    uv sync --no-dev

install-dev:  ## Install all dependencies including dev tools
    uv sync

sync:         ## Sync dependencies from pyproject.toml and update uv.lock
    uv sync

update:       ## Update all dependencies to latest compatible versions
    uv lock --upgrade
    uv sync

lock:         ## Generate/update uv.lock file without installing
    uv lock
```

All script execution goes through `uv run` — never call `python` directly in Makefiles. This ensures the correct virtual environment is always used:

```makefile
verify:
    uv run python verify_setup.py

test:
    uv run pytest

lint:
    uv run ruff check .

type-check:
    uv run mypy . --ignore-missing-imports
```

**Source:** Makefile lines 19-30, 52-55, 94-108.

## Setup Commands

| Command | What It Does |
|---------|-------------|
| `make install` | `uv sync --no-dev` — production deps only |
| `make install-dev` | `uv sync` — all deps including ruff, mypy, pytest |
| `make sync` | Re-sync deps after changing `pyproject.toml` |
| `make update` | `uv lock --upgrade && uv sync` — bump to latest compatible versions |
| `make lock` | `uv lock` — regenerate lockfile without installing |
| `make verify` | `uv run python verify_setup.py` — 8 automated checks |
| `make version` | Print all installed library versions |
| `make quickstart` | `install-dev + version + verify` — new developer onboarding |
| `make dev` | Alias for `install-dev` + prints next steps |
| `make clean` | Remove `__pycache__`, `.pyc`, `.pytest_cache`, `htmlcov`, `.coverage` |

**Source:** Makefile lines 19-51, 183-233.

## Testing Commands

```makefile
test:   ## Run all tests with pytest
    uv run pytest

test-dev:  ## Restart dev containers, run full suite, check compliance
    docker-compose -f docker-compose.dev.yml restart
    uv run pytest -v
    $(MAKE) compliance-check

all-checks: lint type-check test  ## Full quality gate before commit
```

### pytest Coverage Pattern

```bash
# Quiet output
uv run pytest -q

# With coverage report
uv run pytest -q --cov=src --cov-report=term-missing

# Specific module
uv run pytest backend/tests/test_memory_l3a.py -v

# Specific category (used in eval commands)
uv run python scripts/run_batch_evaluation.py --category=hurricane
```

**Source:** Makefile lines 52-92, SKILL.md Common Commands section.

## RAG Knowledge Base Commands

| Command | What It Does |
|---------|-------------|
| `make rag-validate` | Validate datasets before loading (dry run) |
| `make rag-load` | Full load: validate + curated docs + datasets → Qdrant |
| `make rag-load-curated-only` | Load only curated docs, skip large datasets |
| `make rag-load-skip-validation` | Load without pre-validation (faster, less safe) |
| `make rag-test` | Run 3 similarity search tests against loaded knowledge base |

**RAG load pattern:**
```makefile
rag-load:
    uv run python -m backend.src.rag.build_knowledge_base

rag-load-curated-only:
    uv run python -m backend.src.rag.build_knowledge_base --curated-only

rag-load-skip-validation:
    uv run python -m backend.src.rag.build_knowledge_base --skip-validation
```

**Source:** Makefile lines 254-302.

## Memory System Commands

| Command | What It Does |
|---------|-------------|
| `make memory-test` | Test Redis + Neo4j connectivity + run L3a/L3c unit tests |
| `make memory-redis-cli` | Open Redis CLI in running container (auto-detects prod/dev) |
| `make memory-neo4j-browser` | Open Neo4j Browser at `http://localhost:7474` |
| `make memory-clear` | Destructive: flush Redis + delete all Neo4j nodes (5s cancel window) |
| `make memory-stats` | Show Redis hit/miss stats + Neo4j node/relationship counts |

**Auto-detect pattern** (used throughout for prod/dev container detection):
```makefile
REDIS_CONTAINER=$$(docker ps --format '{{.Names}}' | grep 'weather-ai-redis' | head -1)
```

**Source:** Makefile lines 308-405.

## Evaluation Commands

| Command | What It Does |
|---------|-------------|
| `make eval-upload-dataset` | Upload golden dataset to LangSmith |
| `make eval-run-batch` | Run full batch evaluation (all test cases) |
| `make eval-check-gates` | Check quality gates: pass rate ≥85%, safety violations = 0 |
| `make eval-quick` | Quick smoke test: `--max-cases=10` |
| `make eval-category CATEGORY=hurricane` | Run one category (simple/complex/hurricane/edge) |
| `make eval-full` | Full pipeline: upload → run → check gates |
| `make eval-level6` | Run advanced evaluation (BLEU/ROUGE, Snapshot, Retrieval, RAGAS, AgentBench) |
| `make eval-bleu-rouge` | BLEU/ROUGE evaluation only |
| `make eval-ragas` | RAGAS Context Recall evaluation only |
| `make eval-agentbench` | AgentBench evaluation only |

**Parametrized target pattern:**
```makefile
eval-category:
    @if [ -z "$(CATEGORY)" ]; then echo "Error: CATEGORY not specified"; exit 1; fi
    uv run python scripts/run_batch_evaluation.py --category=$(CATEGORY)
```

**Quality gate thresholds** (from `eval-check-gates` target):
- Pass rate: ≥85%
- Effectiveness: ≥85%
- Efficiency: ≥80%
- Robustness: ≥80%
- Safety violations: 0 (zero tolerance)

**Source:** Makefile lines 411-537.

## Docker Commands

### Production vs Development

Two Docker Compose files: `docker-compose.yml` (prod) and `docker-compose.dev.yml` (dev).

| Command | What It Does |
|---------|-------------|
| `make docker-up` | Start all 11 services in production mode |
| `make docker-up-dev` | Start all 11 services in development mode (hot reload, volume mounts) |
| `make docker-down` | Stop and remove production containers |
| `make docker-down-dev` | Stop and remove development containers |
| `make docker-restart` | Restart production containers |
| `make docker-restart-dev` | Restart development containers |
| `make docker-rebuild-dev` | Rebuild images + restart dev containers (after Dockerfile changes) |
| `make docker-logs` | Follow logs from all production containers |
| `make docker-logs-dev` | Follow logs from all development containers |
| `make docker-ps` | Show production container status |
| `make docker-ps-dev` | Show development container status |
| `make docker-health` | Check health status of all 11 services individually |
| `make docker-clean` | Destructive: stop production containers + remove volumes (5s cancel window) |
| `make docker-clean-dev` | Destructive: stop dev containers + remove volumes (5s cancel window) |

**11 services in this stack:**

| Service | Port | Purpose |
|---------|------|---------|
| weather-mcp | 8080 | MCP server |
| hurricane-mcp | 8081 | MCP server (life-safety, never cached) |
| weather-ai-api | 8000 | FastAPI agent service |
| qdrant | 6333 | Vector store (RAG + semantic cache) |
| redis | 6379 | Distributed cache + short-term memory |
| neo4j | 7474/7687 | Long-term graph memory |
| postgres | 5432 | Procedural memory, checkpointing |
| prometheus | 9090 | Metrics |
| grafana | 3001 | Dashboards |
| loki | 3100 | Log aggregation |
| tempo | 3200 | Distributed traces |

**Source:** Makefile lines 541-698.

## Observability Commands

| Command | What It Does |
|---------|-------------|
| `make observability-status` | Check health of Prometheus, Grafana, Loki, Tempo with URLs |
| `make observability-logs` | Follow logs from all 4 observability containers |
| `make grafana-open` | Open `http://localhost:3001` in browser + print dashboard URLs |
| `make prometheus-open` | Open `http://localhost:9090` + print useful PromQL queries |
| `make prometheus-reload` | Hot-reload Prometheus config via `POST /-/reload` |
| `make loki-logs` | Query last 100 log entries from Loki API |
| `make verify-signal-correlation` | Verify metrics/traces/logs correlation (Level 8) |

**Grafana dashboards:**
```
http://localhost:3001/d/signal-correlation   # Signal correlation (metrics + traces + logs)
http://localhost:3001/d/mcp-health           # MCP server health
http://localhost:3001/d/agent-performance    # Agent performance
http://localhost:3001/d/cache-metrics        # Cache hit rates and cost savings
```

**Useful PromQL queries:**
```
# MCP latency p95
histogram_quantile(0.95, sum(rate(mcp_request_latency_seconds_bucket[5m])) by (le))

# Cache hit rate
sum(rate(cache_hits_total[5m])) / sum(rate(cache_requests_total[5m]))

# Agent cost per hour
sum(rate(agent_query_cost_dollars[1h]))
```

**Source:** Makefile lines 700-798.

## Cache Commands (Semantic Cache)

| Command | What It Does |
|---------|-------------|
| `make cache-stats` | `GET /cache/stats` — JSON stats for all tiers |
| `make cache-metrics` | Query Prometheus for hit rate, miss rate, cost savings |
| `make cache-clear` | Destructive: `POST /cache/clear` (prompts for confirmation) |
| `make cache-test-semantic` | Send two similar queries, verify Q3 cache tier appears in response |
| `make cache-test-tool` | Test `@cached_tool` decorator on `get_forecast` |

**Source:** Makefile lines 800-848.

## LangChain Compliance Check

```makefile
compliance-check:  ## Check for deprecated LangChain v1.x patterns
    # Checks:
    # 1. No "from langchain.llms import" (deprecated)
    # 2. No AgentExecutor usage (deprecated in v1.x)
    # 3. No "from typing import Optional" (use | None syntax)
    # 4. No create_react_agent from langgraph.prebuilt (deprecated)
```

Run automatically as part of `test-dev`. Also usable standalone before committing code.

**Source:** Makefile lines 115-162.

## Makefile Structure Pattern

```makefile
.PHONY: help install install-dev sync verify clean test ...

# Colors
BLUE  := \033[0;34m
GREEN := \033[0;32m
RED   := \033[0;31m
NC    := \033[0m

# Self-documenting help (parse ## comments)
help:
    @grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
        awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Composite targets
all-checks: lint type-check test  ## Run all quality checks

# Parametrized targets
eval-category:
    @if [ -z "$(CATEGORY)" ]; then echo "Error: CATEGORY not specified"; exit 1; fi
    @uv run python scripts/run_batch_evaluation.py --category=$(CATEGORY)
```

**Convention:** Every public target has a `## description` comment so `make help` is always accurate.

**Source:** Makefile lines 1-17, 164-165.

---

**Reference:** Patterns from weather-ai-agent-service `Makefile`. Adapt command names, service names, ports, and test counts to your project.
