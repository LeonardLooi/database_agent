---
name: voice-ai-engine-development
description: "Build production-ready real-time conversational voice AI engines using async worker pipelines, Gemini Live API for streaming STT, Gemini TTS for synthesis, LangGraph or Google ADK agents, interrupt handling, and FastAPI WebSocket integration. Use when building voice assistants, real-time voice bots, or conversational AI pipelines with full interrupt support."
allowed-tools: Bash, Read, Write, Edit
metadata:
  triggers: voice AI, voice engine, conversational AI, voice assistant, voice bot, Gemini Live, voice pipeline, STT, TTS, real-time audio, barge-in, interrupt handling, async worker pipeline
  related-skills: voice-ai-development, agentic-ai-dev, google-adk, gemini-api-dev, python-dev
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

## Iron Law

**NO VOICE ENGINE WITHOUT INTERRUPT HANDLING AND ASYNC WORKER ISOLATION — EVERY COMPONENT RUNS IN ITS OWN QUEUE**

A voice engine without interrupts is a demo, not a product. Every worker (transcriber, agent, synthesizer) MUST run in an isolated `asyncio.Queue`-based loop. Interrupt handling MUST be wired before any other feature is added. No exceptions.

# Voice AI Engine Development — Gemini Live API + Python 3.14 + FastAPI

## Quick Scaffold

```bash
uv init voice-engine && cd voice-engine
uv add "google-genai>=1.0.0" "fastapi>=0.135.2" "uvicorn[standard]" \
  "websockets>=13.0" pydantic pydantic-settings structlog \
  "langgraph>=1.0.7" "langchain-core>=1.2.8" \
  "google-adk>=1.28.0" pydub numpy aiolimiter
uv add --dev pytest pytest-asyncio httpx ruff mypy
```

## Process

1. **Scaffold** — `uv init` + install `google-genai` (NOT google-generativeai) and dependencies
2. **Configure** — `core/config.py` with pydantic-settings, `.env`, structured logging (no `print()`)
3. **Implement BaseWorker** — asyncio.Queue input/output, `start()`, `_run_loop()`, `terminate()`
4. **Implement GeminiTranscriberWorker** — WebSocket to Gemini Live API, mute/unmute for echo prevention
5. **Implement Agent Worker** — either `LangGraphAgentWorker` (StateGraph) or `ADKAgentWorker` (SequentialAgent)
6. **Implement GeminiSynthesizerWorker** — `gemini-2.5-flash-tts-preview` or `gemini-2.5-pro-tts-preview`
7. **Wire Pipeline** — transcriber → agent → synthesizer via asyncio.Queue; `StreamingConversation` orchestrator
8. **Add Interrupt System** — `InterruptibleEvent`, `broadcast_interrupt()`, rate-limited chunk playback, mute logic
9. **Expose WebSocket** — FastAPI `/conversation` endpoint, `asynccontextmanager` lifespan (NEVER `@app.on_event`)
10. **Test** — unit test each worker in isolation, integration test full pipeline, test interrupt path
11. **Error Handling** — every except block MUST log + rethrow; no silent returns; no mock data

## Key Patterns

| Pattern | Implementation | Reference |
|---------|---------------|-----------|
| Worker Pipeline | `BaseWorker` → `asyncio.Queue` → isolated `_run_loop` | `reference/worker-pipeline.md` |
| Gemini Live STT | `GeminiTranscriberWorker` — WebSocket to `gemini-live-2.5-flash-native-audio` | `reference/worker-pipeline.md` |
| Gemini TTS | `GeminiSynthesizerWorker` — `gemini-2.5-flash-tts-preview` / `gemini-2.5-pro-tts-preview` | `reference/worker-pipeline.md` |
| Interrupt System | `InterruptibleEvent` + `broadcast_interrupt()` + rate-limited chunks + transcriber mute | `reference/interrupt-handling.md` |
| Provider Factory | `VoiceComponentFactory` — config-driven worker creation | `reference/worker-pipeline.md` |
| WebSocket Integration | FastAPI `/conversation` + `asynccontextmanager` lifespan + `WebsocketOutputDevice` | `reference/worker-pipeline.md` |
| Error Recovery | Worker loop catches + logs + reraises; session reconnect for Gemini Live timeouts | `reference/interrupt-handling.md` |

## Documentation Sources

Before generating code, consult these sources:

| Source | URL / Tool | Purpose |
|--------|-----------|---------|
| Gemini Live API | `https://ai.google.dev/gemini-api/docs/llms.txt` | Live API WebSocket protocol, audio format, barge-in |
| google-genai SDK | Context7 MCP → resolve `google-genai` | Current SDK API signatures |
| LangGraph | `https://langchain-ai.github.io/langgraph/llms-full.txt` | StateGraph, nodes, edges |
| Google ADK | Context7 MCP → resolve `google-adk` | SequentialAgent, session patterns |
| FastAPI | Context7 MCP → resolve `fastapi` | WebSocket, lifespan patterns |

## Reference Files

| File | Content | When to Use |
|------|---------|-------------|
| `reference/gemini-provider-setup.md` | google-genai install, Live API WebSocket setup, model names, audio format, auth, rate limits | First — before writing any Gemini code |
| `reference/worker-pipeline.md` | BaseWorker/BaseTranscriber/BaseAgent/BaseSynthesizer + GeminiTranscriberWorker + GeminiSynthesizerWorker + LangGraphAgentWorker + ADKAgentWorker + FastAPI wiring | Core pipeline implementation |
| `reference/interrupt-handling.md` | InterruptibleEvent, broadcast_interrupt, rate-limited playback, transcriber mute, state machine, graceful shutdown | Interrupt system implementation |
| `reference/provider-comparison.md` | Gemini vs Deepgram vs ElevenLabs vs Azure — latency, cost, features, when to use alternatives | Provider selection |
| `reference/common-pitfalls.md` | Audio jumping, echo feedback, interrupts not working, Gemini-specific traps, session timeouts | Debugging and prevention |

## Common Commands

```bash
uvicorn src.main:app --reload                          # Run dev server with hot reload
pytest -q                                              # Run all tests
pytest -q tests/test_workers.py                        # Test worker isolation
pytest -q tests/test_interrupt.py                      # Test interrupt path
ruff check --fix .                                     # Lint and auto-fix
ruff format .                                          # Format code
mypy src/                                              # Type check
```

## Error Handling

**Iron rule:** Every `except` block in a worker loop MUST:
1. Log with `structlog` at `error` level (include full exception context)
2. Either rethrow OR return a proper error state (never return empty/None/mock)

```python
# Required pattern in every worker loop
async def _run_loop(self) -> None:
    while self.active:
        try:
            item = await self.input_queue.get()
            await self.process(item)
        except asyncio.CancelledError:
            raise  # Never swallow CancelledError
        except Exception as exc:
            self._log.error("worker_error", worker=self.__class__.__name__, error=str(exc), exc_info=True)
            # Continue loop — worker recovers from transient errors
            # For fatal errors: self.terminate(); raise
```

**Gemini Live session timeouts:** Sessions expire after ~10 minutes. Implement reconnect with exponential backoff. See `reference/interrupt-handling.md` § Error Recovery.

**No `print()` anywhere.** Use `structlog.get_logger()`.

## Post-Code Review

After writing voice engine code, dispatch:
- `security-reviewer` — WebSocket input validation, API key handling
- `agentic-ai-reviewer` (if LangGraph agent) — graph correctness, iteration limits
- `code-reviewer` — async patterns, resource cleanup, error handling
