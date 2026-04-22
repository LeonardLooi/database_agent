# Blackbox — Prompt Audit Log
# Append-only. Raw user inputs for session auditability.

## 2026-04-17T03:12:42Z
You are a senior full-stack engineer. Build a production-ready, modern chatbot web application with the following stack and requirements.

--- STACK ---
Frontend : Angular 21 (standalone components, Signals API, inject() pattern)
Backend  : Python FastAPI with native WebSocket support
Styling  : Tailwind CSS v4 + Angular CDK
State    : Angular Signals + RxJS WebSocketSubject (no NgRx)
Realtime : WebSocket at ws://host/ws/chat?token=
LLM      : Pluggable provider system — Claude, OpenAI, Gemini, or any future provider
           swappable at runtime via LLM_PROVIDER env var or per-request model field

--- LLM PROVIDER ABSTRACTION (backend) ---
Design an abstract base class and concrete provider implementations:

# app/services/llm/base.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator
from app.schemas.ws_messages import MsgIn

class BaseLLMProvider(ABC):
    """All providers must implement these two methods."""

    @abstractmethod
    async def stream(
        self,
        messages: list[MsgIn],
        model: str,
        temperature: float,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Yield string tokens as they arrive from the LLM."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[MsgIn],
        model: str,
        max_tokens: int = 128,
    ) -> str:
        """Return a complete (non-streaming) response string."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def default_model(self) -> str: ...

    @property
    @abstractmethod
    def available_models(self) -> list[str]: ...

# app/services/llm/providers/anthropic_provider.py
class AnthropicProvider(BaseLLMProvider):
    provider_name = "anthropic"
    default_model = "claude-sonnet-4-20250514"
    available_models = ["claude-opus-4-20250514", "claude-sonnet-4-20250514", "claude-haiku-4-20251001"]
    # Uses: import anthropic; anthropic.AsyncAnthropic()
    # stream: async with client.messages.stream(...) as s: async for t in s.text_stream: yield t
    # generate: resp = await client.messages.create(...); return resp.content[0].text

# app/services/llm/providers/openai_provider.py
class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"
    default_model = "gpt-4o"
    available_models = ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"]
    # Uses: from openai import AsyncOpenAI
    # stream: async for chunk in await client.chat.completions.create(stream=True, ...):
    #   if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
    # generate: resp = await client.chat.completions.create(stream=False, ...); return resp.choices[0].message.content

# app/services/llm/providers/gemini_provider.py
class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"
    default_model = "gemini-2.0-flash"
    available_models = ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    # Uses: import google.generativeai as genai (google-generativeai)
    # Normalise roles: Gemini uses "user"/"model" — map "assistant" → "model"
    # stream: response = await model.generate_content_async(contents, stream=True)
    #   async for chunk in response: yield chunk.text
    # generate: resp = await model.generate_content_async(contents); return resp.text

# app/services/llm/factory.py
class LLMProviderFactory:
    _registry: dict[str, type[BaseLLMProvider]] = {
        "anthropic": AnthropicProvider,
        "openai":    OpenAIProvider,
        "gemini":    GeminiProvider,
    }

    @classmethod
    def register(cls, name: str, provider_cls: type[BaseLLMProvider]) -> None:
        """Register a new provider at runtime — open/closed principle."""
        cls._registry[name] = provider_cls

    @classmethod
    def create(cls, provider_name: str | None = None) -> BaseLLMProvider:
        name = provider_name or settings.LLM_PROVIDER  # fallback to env
        if name not in cls._registry:
            raise ValueError(f"Unknown LLM provider: '{name}'. Registered: {list(cls._registry)}")
        return cls._registry[name]()

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._registry)

# app/services/llm_service.py (thin orchestration layer — unchanged interface for callers)
class LLMService:
    def __init__(self, provider: BaseLLMProvider | None = None):
        self.provider = provider or LLMProviderFactory.create()

    async def stream(self, messages, model, temperature) -> AsyncGenerator[str, None]:
        model = model or self.provider.default_model
        async for token in self.provider.stream(messages, model, temperature):
            yield token

    async def generate_title(self, content: str) -> str:
        prompt = [{"role": "user", "content": f"Reply with ONLY a 4-word title. Message: {content}"}]
        # Always use the cheapest/fastest model per provider for title generation
        fast_model = self.provider.available_models[-1]
        return await self.provider.generate(prompt, model=fast_model, max_tokens=20)

Callers (chat_ws.py, health.py) only ever reference LLMService — never a concrete provider directly.

--- MODEL RESOLUTION RULES ---
1. If the WS message includes a "model" field AND it starts with the active provider's prefix → use it as-is
2. If "model" field references a different provider (e.g. "gpt-4o" when provider=anthropic) → resolve via model-to-provider map, swap provider on the fly
3. If "model" field is empty → use provider.default_model
Model-to-provider map (in factory.py):
  { "gpt-4o": "openai", "gpt-4o-mini": "openai", "o1": "openai", "o3-mini": "openai",
    "claude-opus-4-20250514": "anthropic", "claude-sonnet-4-20250514": "anthropic", "claude-haiku-4-20251001": "anthropic",
    "gemini-2.5-pro": "gemini", "gemini-2.0-flash": "gemini", "gemini-2.0-flash-lite": "gemini" }

--- WEBSOCKET PROTOCOL ---
Client → Server (JSON):
  { "type": "message", "conversation_id": "",
    "messages": [{"role":"user"|"assistant","content":"..."}],
    "model": "", "temperature": 0.7 }
  { "type": "ping" }

Server → Client (JSON):
  { "type": "delta",    "content": "" }
  { "type": "done",     "conversation_id": "", "token_count": 123, "provider": "", "model": "" }
  { "type": "error",    "message": "", "code": 400|429|500 }
  { "type": "pong" }
  { "type": "title",    "conversation_id": "", "title": "<4-word title>" }
  { "type": "providers","data": [{"provider":"anthropic","models":[...]}, ...] }  ← sent on connect

--- FRONTEND REQUIREMENTS ---
1. On WS connect, server sends a "providers" event → Angular stores available providers+models in ProvidersService signal
2. Model selector in ChatInputComponent shows grouped options: Anthropic / OpenAI / Gemini sections
3. Selecting a model from any provider sends the correct model string; the backend resolves the provider
4. Message bubble footer shows both provider name and model name from the "done" event
5. All other frontend requirements identical to the WebSocket spec (ChatWsService, ConversationService, Signals, reconnect, heartbeat, CDK virtualscroll, markdown, etc.)

--- BACKEND REQUIREMENTS (non-LLM parts same as WebSocket spec) ---
1. FastAPI lifespan, CORS, ConnectionManager, JWT auth on WS query param
2. REST: POST/GET/DELETE /api/conversations, GET /api/conversations/{id}/messages, GET /health
3. /health includes: { status, db, ws_connections, active_provider, available_providers, version }
4. SQLAlchemy async + aiosqlite + Alembic; Pydantic v2; structlog; pydantic-settings
5. Config (.env): ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, LLM_PROVIDER=anthropic,
   SECRET_KEY, DATABASE_URL, CORS_ORIGIN, WS_HEARTBEAT_INTERVAL=25
6. Install all three provider SDKs: anthropic>=0.30, openai>=1.0, google-generativeai>=0.8
   Each provider only initialises its client if its API key is present in settings — no crash on missing keys

--- ARCHITECTURE ---
chatbot/
  frontend/
    src/app/
      core/services/  chat-ws.service.ts, conversation.service.ts, providers.service.ts, auth.service.ts
      features/chat/  chat-shell, chat-window, chat-input (model selector grouped by provider)
      features/sidebar/
      shared/components/message-bubble (shows provider+model in footer)
      shared/models/chat.models.ts (WsIncoming includes providers event type)
  backend/
    app/
      services/
        llm/
          base.py
          factory.py
          providers/
            anthropic_provider.py
            openai_provider.py
            gemini_provider.py
        llm_service.py            ← thin orchestration, all callers use this
      api/routes/  chat_ws.py, conversations.py, auth.py, health.py
      core/        config.py, database.py, security.py, ws_manager.py
      models/      conversation.py
      schemas/     ws_messages.py, conversation.py
    alembic/
  docker-compose.yml

--- DELIVERABLES (in order) ---
1. docker-compose.yml
2. backend/app/core/config.py
3. backend/app/services/llm/base.py
4. backend/app/services/llm/factory.py
5. backend/app/services/llm/providers/anthropic_provider.py
6. backend/app/services/llm/providers/openai_provider.py
7. backend/app/services/llm/providers/gemini_provider.py
8. backend/app/services/llm_service.py
9. backend/app/core/ws_manager.py
10. backend/app/api/routes/chat_ws.py
11. backend/app/main.py
12. frontend/src/app/shared/models/chat.models.ts
13. frontend/src/app/core/services/providers.service.ts
14. frontend/src/app/core/services/chat-ws.service.ts
15. frontend/src/app/core/services/conversation.service.ts
16. frontend/src/app/features/chat/chat-input.component.ts  ← grouped model selector
17. frontend/src/app/features/chat/chat-shell.component.ts
18. frontend/src/app/shared/components/message-bubble.component.ts

Generate each file completely — no placeholders, no "// TODO" stubs.
---

## 2026-04-17T03:35:47Z
could not find .env.example file
---

## 2026-04-17T03:57:49Z
update requirements.txt version for python 3.14.4. Consider not puting version number if it will not break the functionality
---

## 2026-04-17T04:08:23Z
update ./chatbot/frontend/package.json package number to match with node version v24.15.0 and npm version 11.21.1 and angular version 21
---

## 2026-04-17T04:16:15Z
update ./chatbot/frontend/package.json package number to match  
  with node version v24.15.0 and npm version 11.21.1 and angular  
  version 21.2.7. make sure you test it before stopping
---

## 2026-04-17T04:41:42Z
run npm start at chatbot/frontend and fix all the error encountered
---

## 2026-04-17T04:47:55Z
the angular UI is not display properly. run ng serve and check the output and fix the UI. test with input message to check if backend is working properly. fix all problems
---

## 2026-04-17T05:57:44Z
the UI is very ugly that the icon are extremely big and all background is dark. Make a modernise layout
---

## 2026-04-17T07:15:55Z
the UI is very ugly that the icon are extremely big and all 
   background is dark. Make a modernise layout using frontend-design skill
---

## 2026-04-17T07:38:14Z
improve the background color. I do not like all black
---

## 2026-04-17T07:45:29Z
i do not see white, cream and teal accents. please update the UI/UX style.
---

## 2026-04-17T07:50:06Z
improve the UI UX to have toggle between light and dark mode
---

## 2026-04-17T07:55:34Z
chatbox/backend uvicorn app.main:app --reload address already in use. Fix it.
---

## 2026-04-17T07:56:20Z
improve the script to auto kill previous uvicorn process or suggest another port
---

## 2026-04-17T07:58:16Z
i am not able to type message at the UI. check why
---

## 2026-04-17T08:03:37Z
make app-sidebar collapsible. when it is collapsed, new-chat-area become a minimalist floating bubble
---

## 2026-04-17T08:27:36Z
the expand icon  and floating bubble is blocking the other ui
---

## 2026-04-17T08:32:47Z
make the new chat button proportional after collapse. make the expand button more intuitive for clicking after collapse
---

## 2026-04-17T09:31:55Z
activate backend and fix all the errors
---

## 2026-04-17T09:40:55Z
run backend and test chatting with aws_provider, fix all the errors.
---

## 2026-04-17T09:56:40Z
<task-notification>
<task-id>bxoa4uwbb</task-id>
<tool-use-id>toolu_01Bd1H6BVk7RDiN2AUyKN5PU</tool-use-id>
<output-file>/private/tmp/claude-502/-Users-leonardlooi-Documents-Database-Agent/d6ac232c-6dcd-4e1a-a063-de22bf707eba/tasks/bxoa4uwbb.output</output-file>
<status>completed</status>
<summary>Background command "Inspect BedrockModel constructor and methods" completed (exit code 0)</summary>
</task-notification>
---

## 2026-04-17T09:56:40Z
<task-notification>
<task-id>bl42uukts</task-id>
<tool-use-id>toolu_017n7ZeU3Aepj2n9a5DyTBze</tool-use-id>
<output-file>/private/tmp/claude-502/-Users-leonardlooi-Documents-Database-Agent/d6ac232c-6dcd-4e1a-a063-de22bf707eba/tasks/bl42uukts.output</output-file>
<status>completed</status>
<summary>Background command "Inspect BedrockModel API" completed (exit code 0)</summary>
</task-notification>
---

## 2026-04-17T10:01:41Z
i have input AWS credential. run backend and test chatting with aws_provider, fix all the errors.
---

## 2026-04-17T10:05:26Z
connection rejected at backend
---

## 2026-04-17T10:13:41Z
review and test the entire architecture design
---

## 2026-04-17T10:23:02Z
generated the title of the chat automatically
---

## 2026-04-17T10:27:22Z
use ui-ux-pro-max skills to improve the ui
---

## 2026-04-17T10:39:17Z
group and collapse all unavaialble model and disabled from selection
---

## 2026-04-17T10:44:34Z
rewind to before group and collapse all unavaialble model and disabled from selection because this is broken
---

## 2026-04-17T10:47:30Z
update angular to replace existing port
---

## 2026-04-17T10:51:06Z
fix angular  port 4200  not connecting to backend?
---

## 2026-04-18T02:34:41Z
 source /Users/leonardlooi/Documents/Database_Agent/.venv/bin/activate
---

## 2026-04-18T02:40:50Z
scan through entire repository in database_agent/, remove duplicated file with suffix 2 (example: .claude/docker 2.md)
---

## 2026-04-18T02:47:06Z
<task-notification>
<task-id>beavm4lm5</task-id>
<tool-use-id>toolu_0193cXC7WbWb1T7kECW6vs4d</tool-use-id>
<output-file>/private/tmp/claude-502/-Users-leonardlooi-Documents-Database-Agent/3704caaa-088b-4db6-b4ef-1f5d53f0ece2/tasks/beavm4lm5.output</output-file>
<status>completed</status>
<summary>Background command "Find all files with " 2" in their names" completed (exit code 0)</summary>
</task-notification>
---

## 2026-04-18T02:47:11Z
<task-notification>
<task-id>badcrqabj</task-id>
<tool-use-id>toolu_01TiPjxprm7TxxcL1TMsCFAj</tool-use-id>
<output-file>/private/tmp/claude-502/-Users-leonardlooi-Documents-Database-Agent/3704caaa-088b-4db6-b4ef-1f5d53f0ece2/tasks/badcrqabj.output</output-file>
<status>completed</status>
<summary>Background command "Find all files with " 2" in names, wait for completion" completed (exit code 0)</summary>
</task-notification>
---

## 2026-04-18T02:47:11Z
<task-notification>
<task-id>bux4hwpev</task-id>
<tool-use-id>toolu_01PCsM88pv3n5w2fhuNuGLta</tool-use-id>
<output-file>/private/tmp/claude-502/-Users-leonardlooi-Documents-Database-Agent/3704caaa-088b-4db6-b4ef-1f5d53f0ece2/tasks/bux4hwpev.output</output-file>
<status>completed</status>
<summary>Background command "Find duplicate files with space-2 suffix" completed (exit code 0)</summary>
</task-notification>
---

## 2026-04-18T02:48:36Z
update README.md documentation to describe the project
---

## 2026-04-18T02:51:41Z
documentation-generation
---

## 2026-04-18T03:05:29Z
how to activate backend?
---

## 2026-04-18T03:06:54Z
error message no module name app using option 2
---

## 2026-04-18T03:11:15Z
git push to repository with the commit message on  changes made
---

## 2026-04-19T02:30:42Z
/plan-mode-review
---

## 2026-04-19T02:32:15Z
/google-adk
---

## 2026-04-19T02:35:42Z
description: >
  Build a production-grade agentic data chatbot using Google ADK with multi-agent
  orchestration, YAML-driven intent definitions, multi-platform database connectors
  (PostgreSQL, MySQL, Snowflake, BigQuery, MSSQL), Snowflake Cortex integration
  (Analyst, Functions, Search, Agents REST API), cross-agent DataFrame combining in
  Python, and FastAPI + Angular 21 frontend. Use this skill whenever building or
  extending an ADK-based data chatbot, agentic SQL pipeline, Cortex Analyst integration,
  or multi-platform data extraction system.
---

# ADK Agentic Data Chatbot Skill

## What This Skill Covers
- Google ADK orchestrator + specialist sub-agents (LlmAgent, ParallelAgent, SequentialAgent)
- YAML intent definitions (machine config) + Markdown prompt files (LLM instructions)
- Multi-platform database connectors routed per-dataset from YAML
- Session-scoped DataFrame store for cross-agent Python joins
- Snowflake Cortex: Analyst (NL→SQL), Functions (SUMMARIZE/SENTIMENT), Search, Agents API
- Unknown intent detection → semantic clarification before data extraction
- FastAPI SSE streaming gateway + Angular 21 chat service
---

## 2026-04-19T02:36:39Z
B
---

## 2026-04-19T02:42:12Z
description: >
  Build a production-grade agentic data chatbot using Google ADK with multi-agent
  orchestration, YAML-driven intent definitions, multi-platform database connectors
  (PostgreSQL, MySQL, Snowflake, BigQuery, MSSQL), Snowflake Cortex integration
  (Analyst, Functions, Search, Agents REST API), cross-agent DataFrame combining in
  Python, and FastAPI + Angular 21 frontend. If user’s intent is to combine data from two sub-agent, I want each sub-agent tool to return a dataframe and have combine the dataset using Python.

If user’s intent is not defined in YAML definition, guess the best and relevant agent and ask user for the right intent before extracting data.
---
## What This Skill Covers
- Google ADK orchestrator + specialist sub-agents (LlmAgent, ParallelAgent, SequentialAgent)
- YAML intent definitions (machine config) + Markdown prompt files (LLM instructions)
- Multi-platform database connectors routed per-dataset from YAML
- Session-scoped DataFrame store for cross-agent Python joins
- Snowflake Cortex: Analyst (NL→SQL), Functions (SUMMARIZE/SENTIMENT), Search, Agents API
- Unknown intent detection → semantic clarification before data extraction
---

## 2026-04-19T02:43:22Z
build on /chatbot project. use /plan-mode-review first
---

## 2026-04-19T02:58:02Z
I want to keep all the other providers to determine the intent. the ADK suppose to replace Gemini provider only. User can choose any provider and achieve the same goal of finding the right dataset. Bigquery auth is through service account. Keep websocket for ADK and all other providers. Plan and ask me again.
---

## 2026-04-19T03:06:30Z
each provider role is to obtain the intent from user's message. Each Provider will orchestra to find the shared specialist sub-agent (LLM Agent, ParallelAgent, SequentialAgent), YAML intents, DB connectors, dataframe store and so on.
---

## 2026-04-19T03:07:43Z
the goal is that each provider will use their respective LLM to decipher the best orchestration.
---

## 2026-04-19T03:15:20Z
Q1 - Skip PostgreSQL and MySQL in MVP. Include Bigquery and MSSQL in MVP.
---

## 2026-04-19T03:15:36Z
Q2 - include COMPLETE/SUMMARIZE function
---

## 2026-04-19T03:17:21Z
Q3 - after agent loop returns dataframe, get provider LLM write in natural-language explanation, return raw data table in csv, return formatted table in chat, return the SQL and Python code used to produce the result.
---

## 2026-04-19T04:42:18Z
MSSQL use pyodbc. C1 - bigquery service account is by logging in to team space and it will auto resolve authentication. C2 - Redis be in MVP scope. C3 - no feature flag. do not delete gemini_provider.py, keep the file name and replace the code with adk_provider
---

## 2026-04-19T04:46:23Z
/plan-mode-review review the plans and handle all potential edge cases
---

## 2026-04-19T04:54:08Z
start
---

## 2026-04-19T05:03:21Z
start
---

## 2026-04-19T05:47:05Z
git push with commit messages describing the right changes
---

## 2026-04-20T12:42:01Z
fix the error INFO:     127.0.0.1:50697 - "WebSocket /ws/chat?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJndWVzdF83NmFlMzRlMzc1YTEiLCJleHAiOjE3NzkyNzc4MDUsImlhdCI6MTc3NjY4NTgwNX0.5j8mex4ApjBautN_BZ-sg5knON_KVWEshDh3PssVAaA" [accepted]
{"user_id": "guest_76ae34e375a1", "total": 1, "event": "ws_connected", "level": "info", "timestamp": "2026-04-20T12:37:23.449618Z"}
INFO:     connection open
INFO:     127.0.0.1:50696 - "GET /api/conversations?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJndWVzdF83NmFlMzRlMzc1YTEiLCJleHAiOjE3NzkyNzc4MDUsImlhdCI6MTc3NjY4NTgwNX0.5j8mex4ApjBautN_BZ-sg5knON_KVWEshDh3PssVAaA HTTP/1.1" 200 OK
{"user_id": "guest_76ae34e375a1", "error": "Error 8 connecting to redis:6379. nodename nor servname provided, or not known.", "event": "ws_unexpected_error", "level": "error", "timestamp": "2026-04-20T12:37:38.572227Z"}
{"user_id": "guest_76ae34e375a1", "total": 0, "event": "ws_disconnected", "level": "info", "timestamp": "2026-04-20T12:37:38.572306Z"}
INFO:     connection closed
---

## 2026-04-20T12:44:59Z
there is no response (.venv) Elises-MacBook-Pro:backend elise$ ./start.sh
==> Using uvicorn: /Users/elise/Desktop/Projects/database_agent/chatbot/.venv/bin/uvicorn
==> Checking port 8000...
==> Starting app.main:app on http://localhost:8000
INFO:     Will watch for changes in these directories: ['/Users/elise/Desktop/Projects/database_agent/chatbot/backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [24487] using WatchFiles
INFO:     Started server process [24496]
INFO:     Waiting for application startup.
{"version": "1.0.0", "provider": "anthropic", "event": "startup", "level": "info", "timestamp": "2026-04-20T12:43:20.555221Z"}
INFO:     Application startup complete.
INFO:     127.0.0.1:50746 - "WebSocket /ws/chat?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJndWVzdF83NmFlMzRlMzc1YTEiLCJleHAiOjE3NzkyNzc4MDUsImlhdCI6MTc3NjY4NTgwNX0.5j8mex4ApjBautN_BZ-sg5knON_KVWEshDh3PssVAaA" [accepted]
{"user_id": "guest_76ae34e375a1", "total": 1, "event": "ws_connected", "level": "info", "timestamp": "2026-04-20T12:43:26.629866Z"}
INFO:     connection open
INFO:     127.0.0.1:50745 - "GET /api/conversations?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJndWVzdF83NmFlMzRlMzc1YTEiLCJleHAiOjE3NzkyNzc4MDUsImlhdCI6MTc3NjY4NTgwNX0.5j8mex4ApjBautN_BZ-sg5knON_KVWEshDh3PssVAaA HTTP/1.1" 200 OK
{"user_id": "guest_76ae34e375a1", "error": "Error 61 connecting to localhost:6379. Connection refused.", "event": "ws_unexpected_error", "level": "error", "timestamp": "2026-04-20T12:43:41.517218Z"}
{"user_id": "guest_76ae34e375a1", "total": 0, "event": "ws_disconnected", "level": "info", "timestamp": "2026-04-20T12:43:41.517285Z"}
INFO:     connection closed
---

## 2026-04-20T12:45:36Z
using local dev
---

## 2026-04-20T12:47:51Z
update the script to default not using redis. only use redis if it is enabled in .env
---

## 2026-04-20T12:51:21Z
add AWS credentials to .env
---

## 2026-04-20T12:58:40Z
make the llm_provider to follow .env, else default value
---

## 2026-04-20T13:00:12Z
show only connectable provider or model to user for selection.
---

## 2026-04-20T13:02:49Z
anthropic, openAI and gemini is empty value in .env, but UI is still showing the model for selection
---

## 2026-04-20T13:07:57Z
give me instruction and code to deploy the entire repository to GCP
---

## 2026-04-20T13:11:11Z
ensure that i can run both at local and gcp
---

## 2026-04-20T13:12:13Z
update this instructions in readme.md
---

## 2026-04-20T13:16:36Z
/documentation-generation
---

## 2026-04-20T13:20:46Z
git push with commit message covering the changes
---

## 2026-04-20T14:06:06Z
Objective: after extracting the intent and not able to find the right tool/skills, backend need to return intent clarification to angular UI for user selection

Task: 1. ensure the intent estimation is generated 2. Ensure intent clarification is sent to UI and wait for user selection 3. After user selection, get the available tool else return result using generic llm interpretation 4. Run test to test each scenario
---

## 2026-04-20T14:11:41Z
<task-notification>
<task-id>a433ee5be4262de30</task-id>
<tool-use-id>toolu_01VNz6kD7fgHd1N4pKnYjq4L</tool-use-id>
<output-file>/tmp/claude-0/-home-user-database-agent/5a6b0e6f-5549-4e97-ac9f-08bae6b73c90/tasks/a433ee5be4262de30.output</output-file>
<status>completed</status>
<summary>Agent "Explore backend intent handling and Angular UI structure" completed</summary>
<result>Perfect. Now I have a comprehensive picture. Let me compile the final report:

## Comprehensive Codebase Exploration Report

I've thoroughly explored the database agent codebase. Here's the complete breakdown:

---

### 1. **PROJECT STRUCTURE**

The project is a full-stack AI chatbot with:
- **Backend**: Python 3.12+ / FastAPI / SQLAlchemy async / SQLite
- **Frontend**: Angular 18+ / TypeScript / Tailwind CSS
- **Communication**: WebSocket (primary) + REST APIs

**Directory layout:**
```
/home/user/database_agent/
├── chatbot/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/routes/        (auth, chat_ws, conversations, health)
│   │   │   ├── agent/             (intent_loader, query_router, tools)
│   │   │   ├── services/llm/      (Anthropic, OpenAI, Gemini, AWS providers)
│   │   │   ├── core/              (config, database, security, ws_manager)
│   │   │   ├── models/            (SQLAlchemy ORM for Conversation, Message)
│   │   │   └── schemas/           (Pydantic models for WebSocket frames)
│   │   ├── config/intents/        (YAML intent definitions)
│   │   └── tests/                 (pytest fixtures, agent loop tests)
│   └── frontend/
│       └── src/app/
│           ├── core/services/     (auth, chat-ws, conversation, providers)
│           ├── features/          (chat-window, chat-input, sidebar)
│           └── shared/            (message-bubble component, chat models)
```

---

### 2. **INTENT EXTRACTION &amp; ESTIMATION FLOW**

**How it works:**

1. **Intent Definition** (`intent_loader.py` @ `/home/user/database_agent/chatbot/backend/app/agent/intent_loader.py`)
   - Loads intent definitions from YAML files (`/home/user/database_agent/chatbot/backend/config/intents/sample_intents.yaml`)
   - Each intent has:
     - `name`: unique identifier (no spaces)
     - `description`: human-readable explanation
     - `connectors`: list of database types (snowflake, bigquery, mssql)
     - `keywords`: list of trigger words (e.g., "revenue", "customer")
     - `prompt_file`: optional system prompt
     - `requires_combine`: flag for multi-source queries
   
   Example intents:
   ```yaml
   - name: sales_revenue
     description: "Query sales revenue, order totals, financial metrics"
     connectors: [snowflake]
     keywords: [revenue, sales, orders, total]
   
   - name: customer_data
     description: "Query customer information and profiles"
     connectors: [mssql]
     keywords: [customer, client, contact, profile]
   ```

2. **Query Router** (`query_router.py` @ `/home/user/database_agent/chatbot/backend/app/agent/query_router.py`)
   - **Fast keyword-based pre-filter** (no LLM cost):
     - Checks if user message contains any keywords from intents OR generic query signals
     - Generic signals: "select", "show", "list", "get", "fetch", "how many", "revenue", etc.
     - If any keyword matches → routes to **agent loop** (tool use)
     - Otherwise → routes to **freeform stream** (no tools)
   
   Method: `is_data_query(user_message: str) -&gt; bool`

3. **Intent Matching in Agent Loop** (handled by LLM via system prompt)
   - `SharedToolkit.intents_as_system_context()` renders all intents as part of system prompt
   - LLM uses this context to select appropriate tools (query_snowflake, query_bigquery, query_mssql, cortex_analyst, etc.)
   - No explicit disambiguation at this stage — the LLM decides based on description + keywords

---

### 3. **BACKEND COMMUNICATION WITH ANGULAR UI**

**Protocol: WebSocket (bidirectional)**

Location: `/home/user/database_agent/chatbot/backend/app/api/routes/chat_ws.py`

**Message flow:**

```
Client → Server (WsOutgoing):
{
  type: "message" | "ping",
  conversation_id?: string,
  messages?: [{role: "user"|"assistant", content: string}],
  model?: string,
  temperature?: number
}

Server → Client (WsIncoming):
{
  type: "delta" | "done" | "error" | "pong" | "title" | "providers" | "clarification_request" | "agent_response",
  content?: string,
  conversation_id?: string,
  token_count?: number,
  provider?: string,
  model?: string,
  ...
}
```

**WebSocket frames sent:**
1. `{"type": "providers", "data": [...]}` — on connect (LLM providers available)
2. `{"type": "delta", "content": "token"}` — streaming tokens (freeform OR agent explanation)
3. `{"type": "done", ...}` — stream end + metadata
4. `{"type": "clarification_request", "message": "...", "candidates": [...]}` — when intent ambiguous
5. `{"type": "agent_response", ...}` — structured agent response with tables
6. `{"type": "title"}` — generated conversation title (async)
7. `{"type": "error"}` — error message

**Implementation details:**
- Built with Starlette WebSocket + RxJS WebSocketSubject
- Heartbeat ping/pong every 25 seconds
- Auto-reconnect after 3-second delay on disconnect
- Token passed as query parameter: `/ws/chat?token={JWT}`

---

### 4. **TOOLS/SKILLS MATCHED TO INTENTS**

**Tool Definition** (`shared_toolkit.py` @ `/home/user/database_agent/chatbot/backend/app/agent/shared_toolkit.py`)

The **SharedToolkit** singleton exposes 7 canonical tools:

1. **query_snowflake(sql, ctx, label, warehouse, database, schema)** 
   - Executes SQL against Snowflake
   - Stores result in DataFrameStore under label

2. **cortex_analyst(question, ctx, semantic_model_stage_path, label)**
   - Snowflake Cortex ANALYST (natural language → SQL)
   - Requires Enterprise tier

3. **cortex_complete(prompt, ctx, model)**
   - Snowflake Cortex COMPLETE (text generation)

4. **cortex_summarize(text, ctx)**
   - Snowflake Cortex SUMMARIZE

5. **query_bigquery(sql, ctx, label, project_id)**
   - Executes SQL against BigQuery (ADC auth)

6. **query_mssql(sql, ctx, label, server, database)**
   - Executes SQL against MSSQL (pyodbc)

7. **combine_dataframes(label_a, label_b, ctx, join_key, how, result_label)**
   - Joins/merges two previously queried DataFrames
   - Handles type mismatches, missing keys, empty data

8. **ask_clarification(message, ctx, candidates)**
   - Pauses agent loop and asks user a clarifying question
   - Stores pending state in Redis/memory
   - Sends WsClarificationRequest frame to client

**Tool availability:**
- Each provider (Anthropic, OpenAI, Gemini, AWS) gets adapted format:
  - `get_anthropic_tools()` → tool_use schema
  - `get_openai_tools()` → function_calling schema
  - `get_adk_functions()` → raw async callables
  - `get_strands_tools()` → decorated async callables

**Tools matching intents:**
- Intent definitions don't map 1:1 to tools
- Instead, intent **keywords** + **description** help the LLM choose tools
- Multi-source intents (e.g., "sales_vs_crm") use `combine_dataframes` after fetching from multiple databases
- `requires_combine: true` flag signals to the system that dataframe combining may be needed

---

### 5. **ANGULAR UI FOR DISPLAYING AGENT RESPONSES**

**Components:**

1. **ConversationService** (`conversation.service.ts` @ `/home/user/database_agent/chatbot/frontend/src/app/core/services/conversation.service.ts`)
   - Manages conversation state with signals
   - Listens to WebSocket messages: `delta`, `done`, `title`, `error`
   - Updates message content streamily via `onDelta()`
   - Marks message as done via `onDone()` (adds provider/model/tokenCount metadata)

2. **ChatWsService** (`chat-ws.service.ts`)
   - Low-level WebSocket connection management
   - Emits all incoming messages to a Subject
   - Handles reconnection, heartbeat, authentication

3. **ChatWindowComponent** (`chat-window.component.ts`)
   - Displays conversation message list
   - Shows empty state with database icon + prompt suggestions
   - Scrolls to bottom on new messages

4. **MessageBubbleComponent** (`message-bubble.component.ts`)
   - Renders individual messages
   - **User messages**: clean dark pill, right-aligned
   - **Assistant messages**: monospace, left-aligned, left amber border
   - **Streaming indicator**: cursor blink animation
   - **Footer**: provider label (Claude/GPT/Gemini), model shortname, token count
   - **Error state**: red border, error icon

5. **ChatInputComponent** (`chat-input.component.ts`)
   - Model selector dropdown (grouped by provider)
   - Connection status indicator (green dot = connected, red = reconnecting)
   - Textarea with auto-resize (Shift+Enter for newline, Enter to send)
   - Send button (disabled while streaming or disconnected)
   - Hints below input

**Data flow for agent responses:**
```
1. User types "Show top 5 revenue items" → sendMessage()
2. Adds placeholder streaming message to UI
3. Sends WsOutgoing via WebSocket
4. Backend routes to agent loop (keyword match: "revenue")
5. Agent calls query_snowflake → stores DataFrame
6. Agent sends back delta frames streaming the explanation text
7. UI appends each delta to the placeholder message content
8. Agent sends done frame → stops streaming, marks message complete
9. Metadata (provider, model, token_count) attached to message
```

**Note:** Currently, the UI does NOT handle `clarification_request` or `agent_response` frames. These are sent by the backend but the frontend only processes `delta`, `done`, `title`, and `error`.

---

### 6. **EXISTING INTENT CLARIFICATION LOGIC**

**Clarification State** (`clarification_state.py` @ `/home/user/database_agent/chatbot/backend/app/agent/clarification_state.py`)

- **Purpose**: Pause agent loop when intent confidence is low, ask user for clarification
- **Backed by**: Redis (when enabled) or in-memory dict with TTL (5 minutes by default)
- **Key methods**:
  - `set_pending(user_id, conversation_id, question, candidates, original_query)` — saves clarification state
  - `get_pending(user_id, conversation_id)` — retrieves state
  - `is_pending(user_id, conversation_id)` — checks if waiting for answer
  - `clear(user_id, conversation_id)` — removes state after user answers

**Clarification Tools** (`clarification_tools.py`)
- Single function: `ask_clarification(message, ctx, candidates=None)`
- Called by agent during loop when confidence is low
- Sends `WsClarificationRequest` frame to WebSocket
- **Returns**: `{"status": "clarification_sent", "message": "...", "candidates": [...]}`

**Resume flow** (in `chat_ws.py`):
```python
pending = clarification_state.get_pending(user_id, conv_id)
if pending:
    clarification_state.clear(user_id, conv_id)
    # Prepend original query + clarification answer to messages
    resume_prefix = (
        f"[Original question: {pending['original_query']}]\n"
        f"[Clarification answer: {user_content}]"
    )
    messages_for_loop = [
        MsgIn(role="user", content=resume_prefix),
        *incoming.messages[:-1],
        MsgIn(role="user", content=user_content),
    ]
    use_agent_loop = True
```

**Status in agent loop**:
- After each tool call, check: `if ctx.clarification_state.is_pending(...): return result with status="clarification_pending"`
- Frontend doesn't currently handle this — it's defined but unused in UI

---

### 7. **EXISTING INTENT HANDLING TESTS**

Location: `/home/user/database_agent/chatbot/backend/tests/`

**Test files:**

1. **test_intent_loader.py**
   - `test_loads_valid_intent()` — loads single intent from YAML
   - `test_multiple_files_merged()` — merges intents from multiple YAML files
   - `test_empty_directory()` — handles empty intent directory
   - `test_missing_required_field_raises()` — validates required fields

2. **test_query_router.py**
   - `test_sql_keyword_triggers_data_query()` — "SELECT *" → is_data_query=true
   - `test_revenue_keyword_triggers_data_query()` — intent keyword triggers agent
   - `test_customer_keyword_triggers_data_query()` — customer keyword triggers agent
   - `test_freeform_chat_not_data_query()` — "hello" → is_data_query=false
   - `test_explain_code_not_data_query()` — "explain Python" → is_data_query=false
   - `test_case_insensitive()` — case-insensitive keyword matching

3. **test_clarification_flow.py**
   - `test_set_and_get_pending()` — stores/retrieves clarification state
   - `test_clear_removes_state()` — clears pending state
   - `test_not_pending_by_default()` — no pending state initially
   - `test_different_conversations_isolated()` — per-conversation isolation

4. **test_agent_loop.py**
   - `test_agent_loop_result_defaults()` — AgentLoopResult initialization
   - `test_agent_loop_result_error_status()` — error status tracking
   - `test_agent_loop_result_clarification_status()` — clarification_pending status
   - `test_base_provider_run_agent_loop_raises()` — NotImplementedError for base class
   - `test_dataframe_store_round_trip()` — store/retrieve DataFrames
   - `test_dataframe_store_returns_none_for_missing()` — missing key handling
   - `test_dataframe_store_list_labels()` — lists all labels in session

5. **test_combine_tools.py**
   - Tests for multi-source DataFrame joining

**Test fixtures** (conftest.py):
- `fake_redis` — FakeRedis instance for testing
- `store` — DataFrameStore with fake Redis
- `clarification_state` — ClarificationState with fake Redis
- `ctx` — AgentToolContext with injected dependencies
- `sample_df` — 3-row Pandas DataFrame for testing

---

### 8. **KEY DATA STRUCTURES &amp; SCHEMAS**

**WebSocket Message Schemas** (`ws_messages.py`):
```python
# Incoming
WsIncoming: {"type": "message"|"ping", "conversation_id": str, "messages": list, "model": str, "temperature": float}

# Outgoing frames
WsDelta: {"type": "delta", "content": str}
WsDone: {"type": "done", "conversation_id": str, "token_count": int, "provider": str, "model": str}
WsError: {"type": "error", "message": str, "code": int}
WsClarificationRequest: {"type": "clarification_request", "message": str, "candidates": list[str]}
WsAgentResponse: {"type": "agent_response", "explanation": str, "table_md": str, "csv": str, "sql_used": list[str], "truncated": bool, "row_count": int, ...}
```

**Agent Loop Result**:
```python
@dataclass
class AgentLoopResult:
    explanation: str = ""
    final_label: str = ""
    sql_used: list[str] = []
    python_used: str = ""
    truncated: bool = False
    row_count: int = 0
    status: str = "completed"  # "completed" | "clarification_pending" | "error"
    error: str = ""
```

**Intent Definition**:
```python
@dataclass
class IntentDefinition:
    name: str
    description: str
    connectors: list[ConnectorConfig]
    prompt_file: str = ""
    keywords: list[str] = []
    requires_combine: bool = False
```

---

### 9. **PROVIDER IMPLEMENTATIONS (AGENT LOOP)**

Each LLM provider implements `run_agent_loop()`:

**Anthropic** (`anthropic_provider.py`):
- Uses `messages.create()` with `tools=` parameter
- Loops on `stop_reason == "tool_use"`
- Processes `block.type == "tool_use"` blocks
- Calls toolkit.dispatch() to execute tools
- Appends tool results as `role=user` with `type=tool_result`

**OpenAI** (`openai_provider.py`):
- Uses `chat.completions.create()` with `tools=` parameter
- Loops on `msg.tool_calls` (when not None/empty)
- Parses `tc.function.arguments` as JSON
- Calls toolkit.dispatch() to execute tools
- Appends tool call results as `role=assistant`+`role=user` turn

**AWS / Gemini**: Similar patterns (tool_use blocks vs function_calling)

---

### 10. **RESPONSE FORMATTING &amp; PERSISTENCE**

**ResponseFormatter** (`response_formatter.py`):
- Converts `AgentLoopResult` + stored DataFrames → `WsAgentResponse`
- Retrieves final DataFrame from session store
- Converts to Markdown table (capped at 50 rows in UI)
- Exports full CSV
- Tracks row_count and truncation flag

**Database persistence** (`models/conversation.py`):
- SQLAlchemy ORM: Conversation, Message models
- Async SQLite by default (configurable via DATABASE_URL)
- Conversations: `id`, `user_id`, `title`, `created_at`, `updated_at`
- Messages: `id`, `conversation_id`, `role`, `content`, `provider`, `model`, `token_count`, `created_at`

---

### 11. **CRITICAL GAPS IN CURRENT IMPLEMENTATION**

1. **Frontend doesn't handle agent_response frames** — WsAgentResponse schema exists but isn't rendered (message-bubble only shows text)
2. **Frontend doesn't handle clarification_request frames** — no UI for candidate selection
3. **Intent disambiguation** happens silently via LLM (no explicit confidence scoring or multi-intent matching)
4. **No explicit intent routing** — just keyword pre-filter → agent uses LLM to pick tools
5. **Clarification loop incomplete** — backend can ask questions but frontend can't respond with selections

---

### 12. **FILE PATHS SUMMARY**

**Backend (Intent/Agent):**
- `/home/user/database_agent/chatbot/backend/app/agent/intent_loader.py` — loads YAML intents
- `/home/user/database_agent/chatbot/backend/app/agent/query_router.py` — keyword-based routing
- `/home/user/database_agent/chatbot/backend/app/agent/clarification_state.py` — manages clarification state
- `/home/user/database_agent/chatbot/backend/app/agent/tools/clarification_tools.py` — ask_clarification tool
- `/home/user/database_agent/chatbot/backend/app/agent/tools/query_tools.py` — database query tools
- `/home/user/database_agent/chatbot/backend/app/agent/shared_toolkit.py` — tool registry + dispatch
- `/home/user/database_agent/chatbot/backend/app/agent/dataframe_store.py` — session DataFrame storage
- `/home/user/database_agent/chatbot/backend/app/agent/response_formatter.py` — formats agent responses
- `/home/user/database_agent/chatbot/backend/app/api/routes/chat_ws.py` — WebSocket handler + agent orchestration
- `/home/user/database_agent/chatbot/backend/app/services/llm/base.py` — BaseLLMProvider interface
- `/home/user/database_agent/chatbot/backend/app/services/llm/providers/anthropic_provider.py` — Anthropic agent loop
- `/home/user/database_agent/chatbot/backend/app/services/llm/providers/openai_provider.py` — OpenAI agent loop
- `/home/user/database_agent/chatbot/backend/config/intents/sample_intents.yaml` — example intents

**Frontend (Chat UI):**
- `/home/user/database_agent/chatbot/frontend/src/app/core/services/chat-ws.service.ts` — WebSocket connection
- `/home/user/database_agent/chatbot/frontend/src/app/core/services/conversation.service.ts` — conversation state + message handling
- `/home/user/database_agent/chatbot/frontend/src/app/features/chat/chat-window.component.ts` — message list UI
- `/home/user/database_agent/chatbot/frontend/src/app/features/chat/chat-input.component.ts` — input + send UI
- `/home/user/database_agent/chatbot/frontend/src/app/shared/components/message-bubble.component.ts` — message rendering
- `/home/user/database_agent/chatbot/frontend/src/app/shared/models/chat.models.ts` — TypeScript interfaces

**Tests:**
- `/home/user/database_agent/chatbot/backend/tests/test_intent_loader.py`
- `/home/user/database_agent/chatbot/backend/tests/test_query_router.py`
- `/home/user/database_agent/chatbot/backend/tests/test_clarification_flow.py`
- `/home/user/database_agent/chatbot/backend/tests/test_agent_loop.py`
- `/home/user/database_agent/chatbot/backend/tests/conftest.py`

---

This is a well-structured agent framework with keyword-based intent detection, multi-tool orchestration, and WebSocket streaming. The main opportunity for enhancement is completing the clarification UI and adding explicit intent confidence scoring.</result>
<usage><total_tokens>84225</total_tokens><tool_uses>80</tool_uses><duration_ms>323628</duration_ms></usage>
</task-notification>
---

## 2026-04-20T14:13:36Z
<task-notification>
<task-id>a4e020f24107a7ea7</task-id>
<tool-use-id>toolu_01LQdZYKAkgie6qjas8LntQN</tool-use-id>
<output-file>/tmp/claude-0/-home-user-database-agent/5a6b0e6f-5549-4e97-ac9f-08bae6b73c90/tasks/a4e020f24107a7ea7.output</output-file>
<status>completed</status>
<summary>Agent "Explore test patterns and Angular chat/intent UI" completed</summary>
<result>Perfect! Now I have comprehensive information. Let me create a final summary document by compiling all the findings:

## Comprehensive Codebase Exploration Report

Based on my thorough exploration of `/home/user/database_agent`, here are the findings across all requested areas:

---

## 1. ANGULAR COMPONENTS (Chat, Messaging, User Input)

**Location:** `/home/user/database_agent/chatbot/frontend/src/app/`

### Chat Components:
- **`features/chat/chat-input.component.ts`** - User input textarea with model selector, connection status indicator, send button. Uses Angular 21 signals, reactive forms.
- **`features/chat/chat-window.component.ts`** - Scrollable message display area with empty state UI (data-grid aesthetic). Handles auto-scroll with AfterViewChecked lifecycle.
- **`features/chat/chat-shell.component.ts`** - Likely container for chat-input + chat-window
- **`features/sidebar/sidebar.component.ts`** - Conversation history sidebar

### Shared Components:
- **`shared/components/message-bubble.component.ts`** - Renders individual messages with provider avatars (C/G/N), metadata (model/tokens), streaming cursor blink animation. Converts model names for display (e.g., `amazon.nova-lite-v1:0` → `nova-lite`).

### Service Layer:
- **`core/services/chat-ws.service.ts`** - WebSocket connection management with heartbeat (25s), auto-reconnect (3s), RxJS WebSocketSubject. Handles message routing to `messages$` Subject.
- **`core/services/conversation.service.ts`** - Conversation state management using Angular signals. Loads history from HTTP API, manages active conversation, streams incoming deltas into placeholder messages, handles error states.
- **`core/services/providers.service.ts`** - LLM provider/model selection management.
- **`core/services/auth.service.ts`** - JWT token management.

### Data Models:
- **`shared/models/chat.models.ts`** - TypeScript interfaces for WebSocket frames and app models (see section 2 below).

**Tech Stack:**
- Angular 21.2.7 (standalone components, signals API, OnPush change detection)
- RxJS 7.8.0
- @angular/cdk 21.2.7 (ScrollingModule for virtual scrolling)
- Tailwind CSS 4.2.0
- marked 18.0.0 (for markdown rendering)
- uuid 13.0.0

---

## 2. INTENT-RELATED MODELS/DTOs/TYPES

**Intent Definition Model** (`/home/user/database_agent/chatbot/backend/app/agent/intent_loader.py`):
```python
class IntentDefinition(BaseModel):
    name: str                              # no spaces allowed
    description: str
    connectors: list[ConnectorConfig]      # at least one required
    prompt_file: str = ""
    keywords: list[str] = []
    requires_combine: bool = False

class ConnectorConfig(BaseModel):
    type: Literal["snowflake", "bigquery", "mssql"]
    warehouse: str = ""
    database: str = ""
    schema_name: str = Field(default="PUBLIC", alias="schema")
    project_id: str = ""
    server: str = ""
```

**Intent Loader:** `YAMLIntentLoader` - Loads and validates YAML files from `config/intents/*.yaml`

**Agent Loop Result** (`/home/user/database_agent/chatbot/backend/app/services/llm/base.py`):
```python
@dataclass
class AgentLoopResult:
    explanation: str = ""
    final_label: str = ""
    sql_used: list[str] = []
    python_used: str = ""
    truncated: bool = False
    row_count: int = 0
    status: str = "completed"              # "completed" | "clarification_pending" | "error"
    error: str = ""
```

**Sample Intents File** (`/home/user/database_agent/chatbot/backend/config/intents/sample_intents.yaml`):
```yaml
intents:
  - name: sales_revenue
    description: "Query sales revenue..."
    connectors:
      - type: snowflake
        warehouse: ANALYTICS_WH
        database: SALES_DB
        schema: PUBLIC
    prompt_file: sales_revenue.md
    keywords: [revenue, sales, orders, total]
  
  - name: sales_vs_crm
    requires_combine: true           # Signals multi-connector join
    connectors:
      - type: snowflake
      - type: mssql
```

**Tool Context** (`/home/user/database_agent/chatbot/backend/app/agent/tools/query_tools.py`):
```python
@dataclass
class AgentToolContext:
    user_id: str
    conversation_id: str
    store: "DataFrameStore"
    clarification_state: "ClarificationState"
    websocket: Any                 # For sending WS frames during tool execution
```

---

## 3. TEST FRAMEWORK AND STRUCTURE

**Testing Framework:** pytest with pytest-asyncio

**Test Files Location:** `/home/user/database_agent/chatbot/backend/tests/`

### Key Test Files:
- **`conftest.py`** (40 lines) - Fixtures using `fakeredis.FakeRedis` for mocking Redis, stores (DataFrameStore), contexts
- **`test_intent_loader.py`** (58 lines) - Tests YAML validation, duplicate detection, missing required fields
- **`test_agent_loop.py`** (72 lines) - Tests AgentLoopResult dataclass, provider interface compliance, DataFrame store round-trip
- **`test_clarification_flow.py`** (37 lines) - Tests pause → WS question → resume flow
- **`test_combine_tools.py`** (88 lines) - Tests DataFrame joining (missing keys, schema mismatches, type mismatches, 0-row inputs)
- **`test_query_router.py`** (39 lines) - Tests keyword-based data query classification

### Test Fixtures:
- `fake_redis` - FakeRedis instance
- `store(fake_redis)` - DataFrameStore with fake Redis
- `clarification_state(fake_redis)` - ClarificationState
- `ctx` - AgentToolContext with mocked websocket=None
- `sample_df` - DataFrame with id/name/amount columns

**Frontend Tests:** No `.spec.ts` or `.test.ts` files currently in frontend. Testing would require Karma/Jasmine (Angular default, not explicitly configured in package.json's `test` script).

---

## 4. TECH STACK VERSIONS

### Backend (`/home/user/database_agent/chatbot/backend/requirements.txt`):
```
FastAPI (uvicorn[standard])
websockets
pydantic&gt;=2.0
pydantic-settings
sqlalchemy&gt;=2.0 (alembic)
greenlet, aiosqlite                    # Async SQLite
PyJWT&gt;=2.9
httpx

# LLM providers (minimum versions)
anthropic&gt;=0.40
openai&gt;=1.58
google-generativeai&gt;=0.8
boto3&gt;=1.35
strands-agents&gt;=0.1
google-adk&gt;=1.28.0                     # Google ADK for Gemini agent loop

# DB connectors
snowflake-connector-python&gt;=3.12.0
google-cloud-bigquery&gt;=3.25.0
pyodbc&gt;=5.1.0

# Data processing
pandas&gt;=2.2.0
PyYAML&gt;=6.0.2

# Session store
redis&gt;=5.0.0
fakeredis[aioredis]&gt;=2.26.0

# Testing
pytest&gt;=8.3
pytest-asyncio&gt;=0.24
```

### Frontend (`/home/user/database_agent/chatbot/frontend/package.json`):
```json
{
  "engines": {
    "node": "^20.19.0 || ^22.12.0 || &gt;=24.0.0",
    "npm": "&gt;=10.9.0"
  },
  "dependencies": {
    "@angular/*": "21.2.7",              # Angular 21
    "@angular/cdk": "21.2.7",
    "rxjs": "~7.8.0",
    "tslib": "^2.8.1",
    "uuid": "^13.0.0",
    "zone.js": "~0.16.0",
    "marked": "^18.0.0"
  },
  "devDependencies": {
    "@angular-devkit/build-angular": "21.2.7",
    "@angular/cli": "21.2.7",
    "@angular/compiler-cli": "21.2.7",
    "tailwindcss": "^4.2.0",
    "typescript": "~5.9.3"
  }
}
```

---

## 5. API CONTRACTS &amp; REQUEST/RESPONSE FORMATS

### WebSocket Message Formats

**Location:** `/home/user/database_agent/chatbot/backend/app/schemas/ws_messages.py` and `/home/user/database_agent/chatbot/frontend/src/app/shared/models/chat.models.ts`

#### Client → Server (WsIncoming):
```python
class WsIncoming(BaseModel):
    type: Literal["message", "ping"]
    conversation_id: str = ""
    messages: list[MsgIn] = []           # [{"role": "user"|"assistant", "content": str}]
    model: str = ""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
```

#### Server → Client Frames:

**`delta`** (streaming):
```python
class WsDelta(BaseModel):
    type: Literal["delta"] = "delta"
    content: str                         # Streamed token chunk
```

**`done`** (end of streaming):
```python
class WsDone(BaseModel):
    type: Literal["done"] = "done"
    conversation_id: str
    token_count: int
    provider: str
    model: str
```

**`agent_response`** (structured agent output):
```python
class WsAgentResponse(BaseModel):
    type: Literal["agent_response"] = "agent_response"
    conversation_id: str
    explanation: str                    # NL explanation from agent
    table_md: str                        # GitHub-flavored markdown table (capped at 50 rows)
    csv: str                             # Full raw CSV data
    sql_used: list[str]                  # SQL queries executed
    python_used: str = ""                # Python code for DataFrame combine
    truncated: bool = False              # True if &gt;50 rows
    row_count: int = 0
    provider: str
    model: str
```

**`clarification_request`** (agent-to-user pause):
```python
class WsClarificationRequest(BaseModel):
    type: Literal["clarification_request"] = "clarification_request"
    message: str                         # Question for user
    candidates: list[str] = []           # Optional candidate intents/answers
```

**`agent_progress`** (during multi-turn loop):
```python
class WsAgentProgress(BaseModel):
    type: Literal["agent_progress"] = "agent_progress"
    step: str                            # e.g., "query_snowflake", "combining"
    message: str
```

**`providers`** (on connect):
```python
class WsProviders(BaseModel):
    type: Literal["providers"] = "providers"
    data: list[WsProviderInfo]

class WsProviderInfo(BaseModel):
    provider: str                        # "anthropic", "openai", "gemini", "aws"
    models: list[str]
    default_model: str
```

**`error`** and **`pong`** (self-explanatory)

### REST API Endpoints

**Auth &amp; Conversations** (`/home/user/database_agent/chatbot/backend/app/api/routes/`):
- `GET /api/conversations?token=...` → List ConversationOut[]
- `GET /api/conversations/{id}/messages?token=...` → List MessageOut[]
- `DELETE /api/conversations/{id}?token=...` → Delete conversation
- `POST /api/auth/login` (via routes/auth.py)

**Database Models:**
```python
# Conversation
id: str (UUID)
user_id: str
title: str
created_at: datetime (UTC)
updated_at: datetime (UTC)
messages: relationship[Message]

# Message
id: str (UUID)
conversation_id: str (FK)
role: str ("user" | "assistant")
content: str (Text)
provider: str
model: str
token_count: int
created_at: datetime (UTC)
```

### DataFrameStore (Redis Key Format)
```
df:{user_id}:{conversation_id}:{label}  → JSON (orient='split')
TTL: 3600 seconds
Fallback: In-memory dict (single-worker only)
```

### Shared Tool Schemas (Anthropic/OpenAI):
Each provider receives these canonical tools (see SharedToolkit in `app/agent/shared_toolkit.py`):
- `query_snowflake(sql, warehouse?, database?, schema?, label?)` 
- `cortex_analyst(question, semantic_model_stage_path, label?)`
- `cortex_complete(prompt, model?)`
- `cortex_summarize(text)`
- `query_bigquery(sql, project_id?, label?)`
- `query_mssql(sql, server?, database?, label?)`
- `combine_dataframes(label_a, label_b, join_key?, how?, result_label?)`
- `ask_clarification(message, candidates?)`

---

## 6. CONFIGURATION

**Backend Config** (`/home/user/database_agent/chatbot/backend/app/core/config.py`):
- LLM API keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, AWS credentials (boto3 chain)
- DB: `DATABASE_URL` (default: SQLite)
- Redis: `REDIS_ENABLED`, `REDIS_URL`
- Snowflake: `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`
- BigQuery: `BIGQUERY_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`
- MSSQL: `MSSQL_SERVER`, `MSSQL_DATABASE`, `MSSQL_USERNAME`, `MSSQL_PASSWORD`, `MSSQL_DRIVER`
- Agent: `INTENT_DIR`, `PROMPT_DIR`, `MAX_DATAFRAME_ROWS=10000`, `MAX_TOOL_CALLS=10`, `DATAFRAME_TTL_SECONDS=3600`, `CLARIFICATION_TTL_SECONDS=300`

**Env Files:**
- Primary: `chatbot/backend/.env`
- Fallback: `chatbot/.env`

---

## File Path Summary

| Purpose | File Path |
|---------|-----------|
| Chat Input Component | `/home/user/database_agent/chatbot/frontend/src/app/features/chat/chat-input.component.ts` |
| Chat Window | `/home/user/database_agent/chatbot/frontend/src/app/features/chat/chat-window.component.ts` |
| Message Bubble | `/home/user/database_agent/chatbot/frontend/src/app/shared/components/message-bubble.component.ts` |
| WebSocket Service | `/home/user/database_agent/chatbot/frontend/src/app/core/services/chat-ws.service.ts` |
| Conversation Service | `/home/user/database_agent/chatbot/frontend/src/app/core/services/conversation.service.ts` |
| Chat Models (TS) | `/home/user/database_agent/chatbot/frontend/src/app/shared/models/chat.models.ts` |
| Intent Loader | `/home/user/database_agent/chatbot/backend/app/agent/intent_loader.py` |
| Intent YAML | `/home/user/database_agent/chatbot/backend/config/intents/sample_intents.yaml` |
| WebSocket Route | `/home/user/database_agent/chatbot/backend/app/api/routes/chat_ws.py` |
| WS Message Schemas | `/home/user/database_agent/chatbot/backend/app/schemas/ws_messages.py` |
| Conversation Models (ORM) | `/home/user/database_agent/chatbot/backend/app/models/conversation.py` |
| Conversation Schemas (DTO) | `/home/user/database_agent/chatbot/backend/app/schemas/conversation.py` |
| Agent Loop Base | `/home/user/database_agent/chatbot/backend/app/services/llm/base.py` |
| Anthropic Provider | `/home/user/database_agent/chatbot/backend/app/services/llm/providers/anthropic_provider.py` |
| Shared Toolkit | `/home/user/database_agent/chatbot/backend/app/agent/shared_toolkit.py` |
| Response Formatter | `/home/user/database_agent/chatbot/backend/app/agent/response_formatter.py` |
| DataFrame Store | `/home/user/database_agent/chatbot/backend/app/agent/dataframe_store.py` |
| Query Tools | `/home/user/database_agent/chatbot/backend/app/agent/tools/query_tools.py` |
| Clarification Tools | `/home/user/database_agent/chatbot/backend/app/agent/tools/clarification_tools.py` |
| Query Router | `/home/user/database_agent/chatbot/backend/app/agent/query_router.py` |
| Config | `/home/user/database_agent/chatbot/backend/app/core/config.py` |
| Test Fixtures | `/home/user/database_agent/chatbot/backend/tests/conftest.py` |
| Test: Intent Loader | `/home/user/database_agent/chatbot/backend/tests/test_intent_loader.py` |
| Test: Agent Loop | `/home/user/database_agent/chatbot/backend/tests/test_agent_loop.py` |
| Test: Combine Tools | `/home/user/database_agent/chatbot/backend/tests/test_combine_tools.py` |
| Test: Clarification Flow | `/home/user/database_agent/chatbot/backend/tests/test_clarification_flow.py` |
| Test: Query Router | `/home/user/database_agent/chatbot/backend/tests/test_query_router.py` |
| Build Plan Doc | `/home/user/database_agent/chatbot/docs/plans/2026-04-19-agentic-data-chatbot.md` |</result>
<usage><total_tokens>83868</total_tokens><tool_uses>79</tool_uses><duration_ms>311204</duration_ms></usage>
</task-notification>
---

## 2026-04-22T07:21:30Z
Use .Claude/skills/documentation-generation to Update all documentation including readme. Include the architecture design and logic
---
