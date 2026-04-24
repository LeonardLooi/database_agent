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

## 2026-04-22T07:26:54Z
<task-notification>
<task-id>ad3ca5bd79a19d7a1</task-id>
<tool-use-id>toolu_01NHVuvZEP2jdeKuHHyahhqe</tool-use-id>
<output-file>/tmp/claude-0/-home-user-database-agent/80eede5d-45b4-461c-8df6-0cac70540c7e/tasks/ad3ca5bd79a19d7a1.output</output-file>
<status>completed</status>
<summary>Agent "Codebase exploration for documentation" completed</summary>
<result>Perfect! Now I have a comprehensive understanding of the project. Let me compile the thorough documentation report:

---

## Comprehensive Database Agent Codebase Documentation

### Project Overview

The **Database Agent Chatbot** is a production-grade, full-stack AI chatbot with a Python/FastAPI backend and Angular frontend. It supports multiple LLM providers (Anthropic, OpenAI, Google Gemini via ADK, AWS Bedrock) with real-time streaming via WebSocket and persistent conversation history in SQLite. The system includes an agentic orchestration layer that can route queries to multiple databases (Snowflake, BigQuery, MSSQL) with shared DataFrame management and clarification workflows.

**Current Status:** MVP implementation in progress (approved 2026-04-19)

---

## 1. Project Directory Structure (3 levels deep)

```
/home/user/database_agent/
├── .claude/                           # Claude Code agent &amp; skill configurations
│   ├── agents/                        # 60+ specialized agent definitions
│   ├── commands/                      # Slash command handlers
│   ├── hooks/                         # Pre-commit, workflow automation
│   ├── rules/                         # Core behaviors, verification standards
│   ├── scripts/                       # Utility scripts
│   ├── skills/                        # 80+ technology-specific skill guides
│   ├── hookify/                       # Design system components
│   └── SKILLS_GUIDE.md                # Master index of all skills
├── chatbot/                           # Main application (monorepo)
│   ├── backend/                       # Python FastAPI backend
│   │   ├── app/
│   │   │   ├── agent/                 # Agentic orchestration layer
│   │   │   │   ├── tools/             # Canonical tools (query, combine, clarify)
│   │   │   │   ├── connectors/        # DB connectors (Snowflake, BigQuery, MSSQL)
│   │   │   │   ├── clarification_state.py
│   │   │   │   ├── dataframe_store.py # Redis-backed DataFrame store
│   │   │   │   ├── intent_loader.py
│   │   │   │   ├── query_router.py    # Data query classifier
│   │   │   │   ├── response_formatter.py
│   │   │   │   └── shared_toolkit.py
│   │   │   ├── api/routes/            # API endpoints
│   │   │   │   ├── auth.py            # JWT auth
│   │   │   │   ├── chat_ws.py         # WebSocket orchestration
│   │   │   │   ├── conversations.py   # CRUD conversations
│   │   │   │   └── health.py          # Health check
│   │   │   ├── core/                  # Infrastructure
│   │   │   │   ├── config.py          # Settings from env + .env files
│   │   │   │   ├── database.py        # SQLAlchemy async session
│   │   │   │   ├── security.py        # JWT token ops
│   │   │   │   └── ws_manager.py      # WebSocket connection manager
│   │   │   ├── models/                # SQLAlchemy ORM
│   │   │   │   └── conversation.py    # Conversation + Message models
│   │   │   ├── schemas/               # Pydantic v2 request/response
│   │   │   │   ├── conversation.py
│   │   │   │   └── ws_messages.py     # All WebSocket frame definitions
│   │   │   ├── services/
│   │   │   │   ├── llm/               # LLM provider abstraction
│   │   │   │   │   ├── base.py        # BaseLLMProvider ABC
│   │   │   │   │   ├── factory.py     # Provider discovery &amp; registration
│   │   │   │   │   └── providers/     # Concrete implementations
│   │   │   │   │       ├── anthropic_provider.py    # tool_use loop
│   │   │   │   │       ├── openai_provider.py       # function_calling loop
│   │   │   │   │       ├── gemini_provider.py       # Google ADK
│   │   │   │   │       └── aws_provider.py          # Strands Agent dual mode
│   │   │   │   └── llm_service.py     # Unified LLM interface (stream)
│   │   │   └── main.py                # FastAPI app entry
│   │   ├── config/
│   │   │   ├── intents/               # YAML intent definitions
│   │   │   │   └── sample_intents.yaml
│   │   │   └── prompts/               # LLM prompt templates (Markdown)
│   │   │       ├── sales_revenue.md
│   │   │       └── sales_vs_crm.md
│   │   ├── tests/                     # pytest fixtures + test modules
│   │   │   ├── conftest.py
│   │   │   ├── test_agent_loop.py
│   │   │   ├── test_clarification_flow.py
│   │   │   ├── test_combine_tools.py
│   │   │   ├── test_intent_clarification_integration.py
│   │   │   ├── test_intent_loader.py
│   │   │   └── test_query_router.py
│   │   ├── alembic/                   # Database migrations (SQLAlchemy)
│   │   ├── data/                      # SQLite database &amp; logs
│   │   ├── Dockerfile                 # Container image (Python 3.12+)
│   │   ├── requirements.txt
│   │   ├── start.sh                   # Local dev startup script
│   │   └── alembic.ini
│   ├── frontend/                      # Angular 21 SPA
│   │   ├── src/app/
│   │   │   ├── core/services/         # auth, chat-ws, conversation, providers, theme
│   │   │   ├── features/
│   │   │   │   ├── chat/              # Chat window, input, message bubble
│   │   │   │   └── sidebar/           # Conversation list, new chat
│   │   │   ├── shared/
│   │   │   │   ├── components/        # Reusable UI components
│   │   │   │   └── models/            # TypeScript interfaces
│   │   │   ├── app.component.ts
│   │   │   ├── app.routes.ts
│   │   │   └── app.config.ts
│   │   ├── src/environments/          # env.ts (dev), env.prod.ts (prod)
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── proxy.conf.json            # ng serve proxy for WebSocket
│   ├── docs/plans/                    # Architecture planning docs
│   │   └── 2026-04-19-agentic-data-chatbot.md  # MVP spec
│   ├── env.template                   # Configuration template
│   ├── docker-compose.yml             # Local dev orchestration
│   └── .env                           # (git-ignored) runtime config
├── blackbox/                          # Audit logging
│   ├── session-log.md                 # Change snapshots per session
│   └── audit.md                       # Raw user prompts
├── .mcp.json                          # MCP server registry (20+ servers)
├── .gitignore
├── README.md                          # User-facing getting started
├── CLAUDE.md                          # Developer workflow &amp; tech stack
└── .git/                              # Version control
```

---

## 2. Tech Stack with Versions

### Backend (Python)

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.12+ | Runtime |
| **FastAPI** | Latest | Web framework &amp; WebSocket |
| **Uvicorn** | Latest (standard) | ASGI server |
| **SQLAlchemy** | &gt;=2.0 | Async ORM |
| **Pydantic** | &gt;=2.0 | Data validation (BaseModel + BaseSettings) |
| **Alembic** | Latest | DB migrations |
| **aiosqlite** | Latest | Async SQLite driver |
| **PyJWT** | &gt;=2.9 | JWT token signing/verification |
| **anthropic** | &gt;=0.40 | Anthropic Claude API |
| **openai** | &gt;=1.58 | OpenAI GPT API |
| **google-generativeai** | &gt;=0.8 | Google Gemini API |
| **google-adk** | &gt;=1.28.0 | Google Agent Development Kit (ADK) |
| **boto3** | &gt;=1.35 | AWS Bedrock integration |
| **strands-agents** | &gt;=0.1 | AWS Strands Agent framework |
| **httpx** | Latest | HTTP client (LLM calls) |
| **websockets** | Latest | WebSocket protocol |
| **structlog** | Latest | JSON structured logging |
| **redis** | &gt;=5.0.0 | Session store (DataFrameStore) |
| **fakeredis** | &gt;=2.26.0 (aioredis) | Testing Redis mock |
| **snowflake-connector-python** | &gt;=3.12.0 | Snowflake SQL + Cortex APIs |
| **google-cloud-bigquery** | &gt;=3.25.0 | BigQuery client (ADC auth) |
| **pyodbc** | &gt;=5.1.0 | MSSQL/pyodbc sync connector |
| **pandas** | &gt;=2.2.0 | DataFrame combine + serialization |
| **PyYAML** | &gt;=6.0.2 | Intent definition parsing |
| **pytest** | &gt;=8.3 | Unit testing |
| **pytest-asyncio** | &gt;=0.24 | Async test fixtures |

### Frontend (Angular)

| Component | Version | Purpose |
|-----------|---------|---------|
| **Node.js** | ^20.19 \| ^22.12 \| &gt;=24 | Runtime |
| **npm** | &gt;=10.9.0 | Package manager |
| **Angular** | 21.2.7 | SPA framework (standalone components, Signals) |
| **TypeScript** | ~5.9.3 | Language |
| **RxJS** | ~7.8.0 | Reactive streams |
| **Angular CDK** | 21.2.7 | Component primitives |
| **Tailwind CSS** | 4.2.0 | Utility-first styling |
| **marked** | ^18.0.0 | Markdown rendering (agent responses) |
| **uuid** | ^13.0.0 | ID generation |
| **zone.js** | ~0.16.0 | Angular runtime |

### Infrastructure &amp; Databases

| Component | Version | Purpose |
|-----------|---------|---------|
| **Docker** | Latest | Containerization |
| **Docker Compose** | 3.9 | Local dev orchestration |
| **Redis** | 7-alpine | Session store + DataFrame cache |
| **SQLite** | Async (aiosqlite) | Chat history (default) |
| **PostgreSQL** | Optional (v2) | Production DB (Cloud SQL compatible) |
| **Snowflake** | REST API | Data warehouse + Cortex functions |
| **BigQuery** | REST API (ADC auth) | Data warehouse |
| **MSSQL** | SQL Server 2019+ | Relational database |

---

## 3. Architecture &amp; Data Flow

### High-Level System Diagram

```
Angular 21 SPA (Browser)
  │ HTTP + WebSocket (ws://)
  ├─── POST /auth/login → JWT token
  └─── WS /ws/chat (Bearer token)

FastAPI Backend (Python 3.12)
  │
  ├─── API Routes
  │     ├── /auth (JWT login, verify)
  │     ├── /conversations (CRUD, list)
  │     ├── /health (liveness)
  │     └── /ws/chat (WebSocket handler)
  │
  └─── Orchestration Layer (chat_ws.py)
        │
        ├─── QueryRouter (is_data_query classifier)
        │     ├── Rule-based pre-filter (SQL keywords, intent signals)
        │     └── LLM classification (fallback, confidence scoring)
        │
        ├─── Provider Selection (LLMProviderFactory)
        │     ├── Anthropic → tool_use agentic loop
        │     ├── OpenAI → function_calling agentic loop
        │     ├── Gemini → Google ADK orchestration
        │     └── AWS Bedrock → Strands Agent loop
        │
        ├─── Freeform Path (non-data queries)
        │     └── provider.stream() → tokens → WS delta frames
        │
        └─── Data Query Path (agentic loop)
              │
              ├─── SharedToolkit (singleton)
              │     ├── Tool registration (per-provider format)
              │     ├── Query tools:
              │     │   ├── query_snowflake(sql, warehouse, db, schema)
              │     │   ├── cortex_analyst(question, semantic_model_path)
              │     │   ├── cortex_complete(prompt, model)
              │     │   ├── cortex_summarize(text, model)
              │     │   ├── query_bigquery(sql, project_id)
              │     │   ├── query_mssql(sql, server, database)
              │     │   └── combine_dataframes(df_a_key, df_b_key, join_key, how)
              │     └── Clarification tools:
              │         └── ask_clarification(message, candidates)
              │
              ├─── DataFrameStore (Redis-backed)
              │     └── Key: "df:{user_id}:{conversation_id}:{label}"
              │        TTL: 3600s, JSON serialization (orient='split')
              │
              ├─── ClarificationState (Redis)
              │     └── Suspends loop, sends WS clarification_request
              │        TTL: 300s, resumes on next message
              │
              ├─── DB Connectors (asyncio.to_thread wrapped)
              │     ├── SnowflakeConnector (SQL + Cortex APIs)
              │     ├── BigQueryConnector (ADC auth)
              │     └── MSSQLConnector (pyodbc)
              │
              └─── ResponseFormatter
                    └── Builds WsAgentResponse:
                         - explanation: NL answer by provider LLM
                         - table_md: Markdown-formatted DataFrame table
                         - csv: Raw CSV data
                         - sql_used: List of SQL queries executed
                         - python_used: DataFrame combine code
```

### Request-Response Message Flow

#### 1. WebSocket Connection &amp; Auth
```
Client → WS /ws/chat?token=&lt;jwt_token&gt;
         │
Backend  ├── Decode JWT token
         ├── Create WebSocket connection
         └── Send WsProviders frame (available LLM providers)
```

#### 2. Freeform Chat Message
```
Client → WsIncoming(type="message", content="Hello", model="claude-opus")
         │
Backend  ├── QueryRouter.is_data_query(content) → False
         ├── LLMService.stream(messages, model, provider)
         └── For each token:
             └── WS frame: WsDelta(content=token)
         └── Final: WsDone(token_count, provider, model)
```

#### 3. Data Query with Agent Loop (Agentic)
```
Client → WsIncoming(type="message", content="Revenue by month", model="claude-opus")
         │
Backend  ├── QueryRouter.is_data_query(content) → True
         ├── Select provider (Anthropic/OpenAI/Gemini/AWS)
         ├── provider.run_agent_loop(messages, tools, context)
         │   │
         │   ├─── Iteration 1: LLM + tool calls
         │   │     ├── LLM thinks: "I need to query Snowflake for sales data"
         │   │     ├── Tool call: query_snowflake("SELECT...", ...)
         │   │     ├── Connector: fetch DataFrame (1000 rows)
         │   │     ├── DataFrameStore.set("df:user1:conv1:sales_data", df_json, 3600)
         │   │     └── Return result to LLM
         │   │
         │   ├─── Iteration 2: Process &amp; combine
         │   │     ├── LLM thinks: "I need to combine with product names"
         │   │     ├── Tool call: query_snowflake(...product_table...)
         │   │     ├── DataFrameStore.set("df:user1:conv1:products", df_json, 3600)
         │   │     ├── Tool call: combine_dataframes("sales_data", "products", ...)
         │   │     └── Return combined result
         │   │
         │   └─── Final: LLM generates natural language explanation
         │        &amp; references data keys for response formatting
         │
         └── ResponseFormatter builds WsAgentResponse:
             ├── explanation: "Based on the data, revenue increased 23% YoY..."
             ├── table_md: "| Month | Revenue |\n|-------|----------|\n..."
             ├── csv: "month,revenue\njan,50000\n..."
             ├── sql_used: ["SELECT... FROM sales", "SELECT... FROM products"]
             └── python_used: "df.merge(sales, products, on='product_id')"
             └── WS frame: WsAgentResponse(...)
```

#### 4. Clarification Flow
```
Client → WsIncoming(type="message", content="Show me data about...ambiguous query")
         │
Backend  ├── QueryRouter: intent score = 0.45 (below confidence threshold)
         ├── Candidates = ["Sales Report", "Customer Analysis", "Inventory Check"]
         ├── ClarificationState.save("clarification:user1:conv1", state)
         ├── WS frame: WsClarificationRequest(message="...", candidates=[...])
         └── Loop paused; waiting for user response
         │
Client → WsIncoming(type="message", content="Sales Report")
         │
Backend  ├── ClarificationState.get() → resume loop
         ├── Route to selected intent, run agent_loop normally
         ├── ClarificationState.delete()
         └── Send WsAgentResponse as normal
```

### WebSocket Frame Types

All frames sent/received over `/ws/chat` use Pydantic-validated schemas in `ws_messages.py`:

**Incoming (Client → Backend):**
- `WsIncoming`: type="message" (chat), type="ping" (keepalive)

**Outgoing (Backend → Client):**
- `WsDelta`: Streaming token (freeform chat)
- `WsDone`: End of stream (token count, provider, model)
- `WsError`: Error message + code
- `WsPong`: Response to ping
- `WsTitle`: Auto-generated conversation title
- `WsProviders`: Available LLM providers on connection
- `WsAgentProgress`: Progress during agent loop ("step 1/3: querying database...")
- `WsClarificationRequest`: Ambiguous intent; needs user selection
- `WsAgentResponse`: Final structured response (explanation + table + CSV + SQL)

---

## 4. Key Components &amp; Their Roles

### Backend Core Services

#### **app/core/config.py** — Settings Management
- Pydantic `BaseSettings` with multi-level .env resolution
- LLM provider API keys (Anthropic, OpenAI, Google, AWS)
- Database URLs (SQLite, future PostgreSQL)
- Redis connection + TTL config
- DB connector credentials (Snowflake, BigQuery, MSSQL)
- Agent limits: `MAX_TOOL_CALLS=10`, `MAX_DATAFRAME_ROWS=10000`, `DATAFRAME_TTL_SECONDS=3600`
- CORS, WebSocket heartbeat, debug mode

#### **app/core/database.py** — SQLAlchemy Async
- AsyncSessionLocal factory (aiosqlite for SQLite, future asyncpg for PostgreSQL)
- Base ORM class
- `create_tables()` lifespan hook

#### **app/core/security.py** — JWT Auth
- Token generation (30-day expiry) and validation
- `HS256` algorithm (configurable)

#### **app/core/ws_manager.py** — WebSocket Connection Pooling
- Manages active WebSocket connections per user/conversation
- Broadcast &amp; unicast messaging

#### **app/services/llm/** — Provider Abstraction
- **base.py**: `BaseLLMProvider` ABC with `stream()` and new `run_agent_loop()` methods
- **factory.py**: `LLMProviderFactory` discovers registered providers, filters by API key availability
- **providers/**:
  - `anthropic_provider.py`: Claude with tool_use multi-turn loop
  - `openai_provider.py`: GPT with function_calling loop (preserves o1/o3 overrides)
  - `gemini_provider.py`: **Replaced with Google ADK** (`LlmAgent`, `ParallelAgent`, `SequentialAgent`)
  - `aws_provider.py`: Bedrock with Strands Agent dual-mode (agentic loop + streaming fallback)

#### **app/models/conversation.py** — ORM Models
- `Conversation`: id, user_id, title, created_at, updated_at, messages[]
- `Message`: id, conversation_id, role (user/assistant), content, provider, model, token_count, created_at

#### **app/schemas/** — Pydantic Validation
- `conversation.py`: `MessageOut`, `ConversationOut`, `ConversationWithMessages`
- `ws_messages.py`: 10+ frame types (inbound + outbound)

#### **app/api/routes/chat_ws.py** — WebSocket Orchestration (478 lines)
Key features:
- JWT token decoding on connection
- `QueryRouter` instance (lazy-init, per-worker)
- Route messages: freeform → `llm_service.stream()` OR data query → `provider.run_agent_loop()`
- `ClarificationState` check on every incoming message (resume if pending)
- `DataFrameStore` access for tool results
- Heartbeat ping/pong
- Conversation persistence to SQLite
- WebSocket disconnect handling &amp; loop cancellation
- Error recovery with structured logging

---

### Agent Orchestration Layer

#### **app/agent/query_router.py** — Data Query Classifier
```python
class QueryRouter:
    def is_data_query(query: str) -&gt; IntentEstimationResult:
        # Step 1: Fast keyword matching against _QUERY_SIGNALS + YAML intent keywords
        # Step 2: LLM classification (only if inconclusive)
        # Return: top_intent, confidence (0.0–1.0), is_ambiguous flag, candidates
```

#### **app/agent/intent_loader.py** — YAML Intent Definitions
- Loads YAML from `config/intents/*.yaml`
- Pydantic schema validation
- Intent structure: name, keywords, description, example_query, tools_required

#### **app/agent/dataframe_store.py** — Session DataFrame Cache
```python
class DataFrameStore:
    # Redis-backed (or in-memory fallback when REDIS_ENABLED=false)
    # Key format: "df:{user_id}:{conversation_id}:{label}"
    # Serialization: df.to_json(orient='split') ← protects against pickle RCE
    # TTL: 3600s (configurable DATAFRAME_TTL_SECONDS)
    
    async def set(key, df, ttl)    # Store DataFrame
    async def get(key) -&gt; df       # Retrieve + check expiry
    async def delete(key)          # Explicit cleanup
```

#### **app/agent/clarification_state.py** — Intent Ambiguity Suspension
```python
class ClarificationState:
    # Redis key: "clarification:{user_id}:{conversation_id}"
    # Value: {loop_task_id, candidates, original_query}
    # TTL: 300s (CLARIFICATION_TTL_SECONDS)
    # On next WS message: check → if exists, route as clarification answer
```

#### **app/agent/response_formatter.py** — Structured Response Builder
```python
class ResponseFormatter:
    # Builds WsAgentResponse from:
    # - final_explanation (LLM-generated NL text)
    # - dataframe_labels (keys used: "sales_data", "products")
    # - sql_queries (list of executed SQL strings)
    # - python_code (combine_dataframes Python code)
    
    # Returns WsAgentResponse:
    #   - explanation: str
    #   - table_md: str (markdown-formatted table, limited to 100 rows display)
    #   - csv: str (full CSV export)
    #   - sql_used: list[str]
    #   - python_used: str
    #   - truncated: bool (if &gt;100 rows)
    #   - row_count: int
```

#### **app/agent/shared_toolkit.py** — Tool Registry
```python
class SharedToolkit:
    # Singleton, initialized once per startup
    # Methods per provider format:
    #   - for_anthropic() → {name: str, description: str, input_schema: {...}}
    #   - for_openai() → {name: str, description: str, parameters: {...}}
    #   - for_gemini() → google.adk.Tool objects
    #   - for_aws() → Strands Agent tool format
    
    # Canonical tool names (all providers):
    #   - query_snowflake(sql, warehouse, database, schema) → DataFrame
    #   - cortex_analyst(question, semantic_model_path) → {sql, analysis}
    #   - cortex_complete(prompt, model) → str
    #   - cortex_summarize(text, model) → str
    #   - query_bigquery(sql, project_id) → DataFrame
    #   - query_mssql(sql, server, database) → DataFrame
    #   - combine_dataframes(df_a_key, df_b_key, join_key, how) → DataFrame
    #   - ask_clarification(message, candidates) → suspends loop
```

#### **app/agent/tools/** — Tool Implementations

**query_tools.py:**
- `query_snowflake()`, `query_bigquery()`, `query_mssql()` — execute SQL, return DataFrame
- `cortex_analyst()` — Snowflake Cortex ANALYST (2-step: REST → SQL, execute)
- `cortex_complete()`, `cortex_summarize()` — Snowflake Cortex APIs
- `combine_dataframes()` — pandas merge with validation (handles missing keys, type mismatches)
- Pydantic input schemas for each tool

**clarification_tools.py:**
- `ask_clarification()` — writes to ClarificationState, sends WS frame, suspends loop

**combine_tools.py:**
- DataFrame merge logic, edge case handling

#### **app/agent/connectors/** — Database Adapters

**base.py:**
```python
class BaseConnector(ABC):
    @abstractmethod
    async def execute_query(sql: str) -&gt; DataFrame
    # All sync DB calls wrapped in asyncio.to_thread()
```

**snowflake_connector.py:**
- SQL execution + Cortex ANALYST (semantic model → SQL generation)
- Cortex COMPLETE, SUMMARIZE endpoints
- Error handling: catches `ProgrammingError` for non-Enterprise tier

**bigquery_connector.py:**
- ADC (Application Default Credentials) auth
- BigQuery Client (REST + gRPC)
- Column metadata inference

**mssql_connector.py:**
- pyodbc ODBC Driver 18
- Connection string building
- Sync wrapper: `asyncio.to_thread()`

---

### Frontend (Angular 21)

#### **Core Services (app/core/services/)**

**auth.service.ts:**
- Login (POST /auth/login with email/password)
- Token storage (localStorage)
- Token refresh on app init
- Logout

**chat-ws.service.ts:**
- WebSocket connection (ws:// auto-resolved from window.location)
- Frame handling: delta → stream to Observable, done → complete, error → error
- **New: agent_response frame** → explanation bubble + table markdown + CSV download + SQL/Python collapsible blocks

**conversation.service.ts:**
- CRUD operations: create, list, get by ID, update title, delete
- HTTP client integration

**providers.service.ts:**
- Fetch available LLM providers on app init
- Update when new provider added

**theme.service.ts:**
- Dark/light mode toggle

#### **Features (app/features/)**

**chat/** (Chat window + input):
- `chat-window.component.ts`: Message list (infinite scroll, markdown rendering)
- `chat-input.component.ts`: Input field, model selector, submit button
- Streaming animation: animated cursor, delta tokens append

**sidebar/** (Conversation list):
- `sidebar.component.ts`: List conversations, new chat button, delete conversation

#### **Shared Components (app/shared/)**

**components/**:
- `message-bubble.component.ts`: User/assistant message rendering, markdown → HTML

**models/**:
- `chat.models.ts`: TypeScript interfaces
  - `Message` (id, role, content, provider, model, timestamp)
  - `Conversation` (id, title, created_at, messages[])
  - `AgentResponseFrame` (explanation, table_md, csv, sql_used, python_used)
  - `ClarificationRequestFrame` (message, candidates)

---

## 5. Database Schema

### SQLite (default; async)

**conversations** table:
```sql
CREATE TABLE conversations (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    title VARCHAR DEFAULT 'New Chat',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX user_id
);
```

**messages** table:
```sql
CREATE TABLE messages (
    id VARCHAR PRIMARY KEY,
    conversation_id VARCHAR NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    provider VARCHAR,       -- 'anthropic', 'openai', 'gemini', 'aws'
    model VARCHAR,          -- 'claude-opus', 'gpt-4', etc.
    token_count INTEGER DEFAULT 0,
    created_at DATETIME NOT NULL,
    INDEX conversation_id
);
```

### Redis (session state)

**DataFrames:**
```
Key:   "df:{user_id}:{conversation_id}:{label}"
Value: JSON string (orient='split')
TTL:   3600s
```

**Clarification state:**
```
Key:   "clarification:{user_id}:{conversation_id}"
Value: {loop_task_id: str, candidates: list, original_query: str}
TTL:   300s
```

---

## 6. Configuration &amp; Environment Variables

**chatbot/.env** (from env.template):

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `ANTHROPIC_API_KEY` | At least 1 | "" | Claude API key |
| `OPENAI_API_KEY` | At least 1 | "" | GPT API key |
| `GOOGLE_API_KEY` | At least 1 | "" | Gemini API key |
| `AWS_ACCESS_KEY_ID` | Optional | "" | AWS credentials (or IAM role) |
| `AWS_SECRET_ACCESS_KEY` | Optional | "" | AWS credentials |
| `AWS_REGION` | No | "us-east-1" | AWS Bedrock region |
| `SECRET_KEY` | Yes | dev-placeholder | JWT signing secret (32 bytes) |
| `LLM_PROVIDER` | No | auto | Default provider (fallback: first available) |
| `DATABASE_URL` | No | SQLite @ ./data/chatbot.db | SQLAlchemy async URL |
| `REDIS_ENABLED` | No | false | Enable Redis (default: in-memory) |
| `REDIS_URL` | No | redis://localhost:6379/0 | Redis connection |
| `SNOWFLAKE_ACCOUNT` | Optional | "" | Snowflake account ID |
| `SNOWFLAKE_USER` | Optional | "" | Snowflake user |
| `SNOWFLAKE_PASSWORD` | Optional | "" | Snowflake password |
| `SNOWFLAKE_WAREHOUSE` | Optional | "COMPUTE_WH" | Warehouse name |
| `SNOWFLAKE_DATABASE` | Optional | "" | Database name |
| `SNOWFLAKE_SCHEMA` | Optional | "PUBLIC" | Schema name |
| `SNOWFLAKE_ROLE` | Optional | "" | Role name |
| `BIGQUERY_PROJECT_ID` | Optional | "" | GCP project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | Optional | "" | Path to service account JSON |
| `MSSQL_SERVER` | Optional | "" | SQL Server host |
| `MSSQL_DATABASE` | Optional | "" | Database name |
| `MSSQL_USERNAME` | Optional | "" | Username |
| `MSSQL_PASSWORD` | Optional | "" | Password |
| `MSSQL_DRIVER` | No | "ODBC Driver 18 for SQL Server" | ODBC driver name |
| `CORS_ORIGIN` | No | http://localhost:4200 | CORS allowed origin |
| `WS_HEARTBEAT_INTERVAL` | No | 25 | Ping interval (seconds) |
| `APP_VERSION` | No | "1.0.0" | Version string |
| `DEBUG` | No | false | Enable /docs, verbose logs |
| `INTENT_DIR` | No | ./config/intents | YAML intent path |
| `PROMPT_DIR` | No | ./config/prompts | Prompt template path |
| `MAX_DATAFRAME_ROWS` | No | 10000 | DataFrame row limit |
| `MAX_TOOL_CALLS` | No | 10 | Agent loop iteration cap |
| `DATAFRAME_TTL_SECONDS` | No | 3600 | DataFrame cache TTL |
| `CLARIFICATION_TTL_SECONDS` | No | 300 | Clarification state timeout |

---

## 7. Deployment

### Local Development (no Docker)
```bash
cd chatbot/backend
python -m venv .venv &amp;&amp; source .venv/bin/activate
pip install -r requirements.txt
cp ../env.template ../.env  # edit .env
./start.sh
# OR: uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install &amp;&amp; npm start
# Frontend: http://localhost:4200
# Backend: http://localhost:8000
```

### Docker Compose (local)
```bash
cd chatbot
cp env.template .env  # edit .env
docker compose up --build
# Frontend: http://localhost:4200
# Backend docs: http://localhost:8000/docs (DEBUG=true only)
```

### GCP Cloud Run
- Step 1: Create Artifact Registry, enable APIs
- Step 2: Store secrets in Secret Manager (ANTHROPIC_API_KEY, etc.)
- Step 3: Build &amp; push backend Docker image
- Step 4: Deploy backend to Cloud Run (set env vars + secrets)
- Step 5: Deploy frontend to Cloud Run (set BACKEND_URL)
- Step 6: Update backend CORS to frontend URL
- Optional: Cloud SQL for persistent PostgreSQL database

See README.md § "Deploy to GCP (Cloud Run)" for full commands.

---

## 8. Testing

**Backend (pytest):**
```bash
cd chatbot/backend
source .venv/bin/activate
pytest                        # All tests
pytest --cov=app              # With coverage
pytest -k test_agent_loop     # Single test file
```

**Frontend (ng test):**
```bash
cd chatbot/frontend
ng test                       # Watch mode
ng test --no-watch --code-coverage
```

**Test files** in `backend/tests/`:
- `conftest.py`: Fixtures (AsyncSession, mock Redis, DataFrameStore)
- `test_agent_loop.py`: Provider agent loop correctness
- `test_clarification_flow.py`: Ambiguity → question → resume
- `test_combine_tools.py`: DataFrame merge edge cases
- `test_intent_clarification_integration.py`: End-to-end intent + clarification
- `test_intent_loader.py`: YAML parsing &amp; validation
- `test_query_router.py`: Data query classification

---

## 9. Documentation Files (Complete List)

### Root-Level Documentation
- **README.md** (8.6 KB): User-facing getting started, quick start (local + Docker), configuration table, GCP Cloud Run deployment, feature overview
- **CLAUDE.md** (8.9 KB): Developer workflow, tech stack summary, code conventions, task management, git workflow, self-improvement loop
- **blackbox/session-log.md**: Append-only audit of file changes per session (git snapshots)
- **blackbox/audit.md**: Raw user prompts (prompt audit log)

### Project Planning &amp; Architecture
- **chatbot/docs/plans/2026-04-19-agentic-data-chatbot.md** (11 KB): Approved MVP plan with:
  - Architecture diagram (provider orchestration)
  - File changes table (all new + modified files)
  - MVP scope (included vs. deferred)
  - Known risks &amp; edge cases (A1–A6, Q1–Q6, T1–T4, P1–PR4)
  - Implementation notes (Dockerfile ODBC order, Redis key format, GeminiProvider name constraint, QueryRouter strategy)
  - Implementation order (4 phases)
  - Mutations log (changelog)

### MCP Server Registry
- **.mcp.json** (5.5 KB): 20+ MCP server configurations
  - GitHub Copilot API
  - Angular CLI
  - Chrome DevTools
  - Browser Use
  - Firebase
  - Context7 (documentation)
  - Dart MCP
  - LangChain Docs
  - PostgreSQL
  - Docker
  - Xcode
  - Maestro (mobile testing)
  - ADK Docs (Google Agent Development Kit)
  - Weaviate Docs
  - Stripe, RevenueCat, Voice Mode

### Claude Code Agents &amp; Skills (.claude/)
- **80+ Skills** (agentic-ai-dev, angular-spa, python-dev, database-designer, vector-database, etc.)
- **60+ Agent definitions** (code-reviewer, agentic-ai-reviewer, frontend-design, etc.)
- **Rules** (core-behaviors, verification-and-reporting, code-standards, leverage-patterns)
- **Commands** (slash command handlers)
- **Hooks** (pre-commit, workflow automation)

---

## 10. Key Architectural Decisions

### Provider Abstraction
- Each LLM provider (Anthropic, OpenAI, Gemini, AWS) is a pluggable implementation of `BaseLLMProvider`
- `LLMProviderFactory` auto-discovers providers with configured API keys
- **Per-provider agent loops:** Each uses its native orchestration pattern (tool_use, function_calling, ADK, Strands Agent)

### Agentic Routing
- **QueryRouter** pre-filters with keywords, fallback to LLM classification
- **Data queries** route to provider-specific agent loop (not streaming)
- **Freeform queries** use simple streaming (`stream()` method)
- **Ambiguous queries** pause and request clarification via WS frame

### DataFrame Management
- Redis-backed store (with in-memory fallback) per session
- JSON serialization (`orient='split'`) protects against pickle RCE
- TTL-based auto-cleanup (3600s default)
- Scoped per `{user_id}:{conversation_id}:{label}` to prevent cross-conversation leakage

### Database Connectors
- Synchronous APIs wrapped in `asyncio.to_thread()` for async compatibility
- Snowflake: SQL + Cortex ANALYST (2-step) + COMPLETE/SUMMARIZE
- BigQuery: ADC auth (no explicit key needed if mount ~/.config/gcloud)
- MSSQL: pyodbc ODBC Driver 18 (Dockerfile install order matters)

### Frontend Complexity
- Angular Signals + RxJS (no NgRx)
- Markdown rendering for agent responses (marked library)
- Auto-resolving WebSocket URL from window.location (works in Docker + Cloud Run without rebuild)

---

## 11. Known Limitations &amp; Future Work

### Deferred to v2 (per plan)
- PostgreSQL connector
- MySQL connector
- Snowflake Cortex Search
- Snowflake Cortex Agents REST API
- Redis DataFrameStore multi-worker scaling

### Edge Cases &amp; Risks (from plan, pre-mitigation)
- A1: `GeminiProvider` class name must match factory import
- A2: `run_agent_loop()` uses default `raise NotImplementedError` (non-abstract) during transition
- A3: Clarification flow requires WS multi-turn suspension (Redis-backed state)
- Q1: DB connectors are sync; wrapped in `asyncio.to_thread()`
- Q2: Redis serialization → use JSON (not pickle) to prevent RCE
- PR1: Snowflake Enterprise tier required for Cortex ANALYST (error handling in connector)
- PR2: ODBC Driver 18 must install before pip (Dockerfile order)

---

## Summary

The **Database Agent Chatbot** is a sophisticated, production-ready system that combines:
1. **Multi-provider LLM orchestration** with provider-native agent loops
2. **Agentic data querying** with intent classification, clarification flows, and DataFrame management
3. **Real-time streaming** via WebSocket with structured response frames
4. **Enterprise database support** (Snowflake, BigQuery, MSSQL) with async-safe connectors
5. **Modern frontend** (Angular 21) with markdown rendering and responsive chat UX
6. **Docker-native local dev** (Docker Compose) + GCP Cloud Run deployment

The MVP scope is well-defined, risks are catalogued with mitigations, and the implementation is methodically planned across 4 phases. All code adheres to structured logging, async safety, and security best practices (JWT, secret redaction, Redis JSON serialization).</result>
<usage><total_tokens>81920</total_tokens><tool_uses>88</tool_uses><duration_ms>310964</duration_ms></usage>
</task-notification>
---

## 2026-04-22T11:48:01Z
/plan-mode-review ═══════════════════════════════════════════════════════════════════════════════
CLAUDE CODE — FULL IMPLEMENTATION BRIEF
═══════════════════════════════════════════════════════════════════════════════

You are working on an existing repository. Follow this brief exactly and in
order. Do NOT skip phases. Do NOT stop until all objectives pass their
done criteria and all stress tests are green.

───────────────────────────────────────────────────────────────────────────────
PHASE 0 — DISCOVERY (READ ONLY, NO CHANGES)
───────────────────────────────────────────────────────────────────────────────

Before writing a single line of code:

1. Scan and print the full repository tree (max 3 levels deep)
2. Read every file in full: gemini_provider.py, all existing provider files,
   all deployment configs (Dockerfile, docker-compose*, requirements.txt,
   pyproject.toml, .env.example), all frontend source files, all test files
3. List all environment variables currently in use across the codebase
4. List all existing tools/functions/routes
5. Identify what test framework is in use (pytest, jest, etc.)
6. State any conflicts, ambiguities, or missing files before proceeding
7. Produce a short AUDIT SUMMARY then wait for Phase 1

───────────────────────────────────────────────────────────────────────────────
OBJECTIVE 1 — GCP SHARED SERVICE ACCOUNT VIA ADC + IMPERSONATION
───────────────────────────────────────────────────────────────────────────────

File: gemini_provider.py

Authenticate using Application Default Credentials (ADC) but explicitly
target the team-space shared service account — not the caller's personal
credentials nor the Compute Engine default service account.

Auth resolution priority (implement as _resolve_credentials() helper):

  Priority 1 — Impersonation (production preferred):
    - Triggered when env var GCP_IMPERSONATE_SA is set
    - Value format: shared-sa@project-id.iam.gserviceaccount.com
    - Use google.auth.impersonated_credentials.Credentials
    - Source credentials come from ambient ADC (gcloud or metadata server)
    - Requires roles/iam.serviceAccountTokenCreator on the caller identity
    - No key file needed

  Priority 2 — Key file (local dev fallback):
    - Triggered when GOOGLE_APPLICATION_CREDENTIALS is set to a file path
    - Use google.oauth2.service_account.Credentials.from_service_account_file()
    - Scope: https://www.googleapis.com/auth/cloud-platform

  Priority 3 — Ambient ADC (last resort):
    - google.auth.default() with cloud-platform scope
    - Log a WARNING: "Shared SA not explicitly targeted. Verify ADC identity."

Implementation rules:
- Log WHICH auth path was chosen at INFO level (never log credential values)
- Raise AuthConfigError with actionable remediation message if all paths fail
- Credentials must auto-refresh (use google.auth.transport.requests.Request)
- Add to README: how to configure each auth path for local dev vs production

───────────────────────────────────────────────────────────────────────────────
OBJECTIVE 2 — YAML-DRIVEN AI SKILL EXECUTION (MODEL-AGNOSTIC)
───────────────────────────────────────────────────────────────────────────────

Core concept:
  The active AI model (Gemini, OpenAI, or Anthropic) reads the full YAML skill
  definition — including its instructions, parameters, and execution steps —
  and carries out those instructions directly. The YAML IS the program.
  The AI model IS the executor. There is no separate Python executor function.

─── Skill YAML Schema (skills/<skill_name>.yaml) ───────────────────────────

name: summarise_document
description: >
  Summarise a document provided by the user. Extract key points,
  decisions, and action items. Return a structured summary.
instructions: |
  You are a precise document analyst. When given a document:
  1. Identify the document type (email, report, meeting notes, contract)
  2. Extract a maximum of 5 key points as bullet items
  3. List any decisions made (or state "None identified")
  4. List action items with owner names if present
  5. Produce a one-sentence executive summary
  6. Respond ONLY in the output_format specified below. No preamble.
parameters:
  document_text:
    type: string
    required: true
    description: The full text of the document to summarise
  language:
    type: string
    required: false
    default: "en"
    description: ISO 639-1 language code for the response
output_format: |
  {
    "executive_summary": "...",
    "key_points": ["...", "..."],
    "decisions": ["..."],
    "action_items": [{"task": "...", "owner": "..."}],
    "document_type": "..."
  }
tags: [document, summarisation, extraction]
─────────────────────────────────────────────────────────────────────────────

Implementation requirements:

1. SkillRegistry class (skill_registry.py):
   - Scans skills/*.yaml at startup and builds an in-memory registry
   - Exposes: get_skill(name), list_skills(), get_all_descriptions()
   - Dev mode: watch skills/ directory for YAML changes and hot-reload
   - Validates YAML schema on load; log WARNING and skip invalid files

2. BaseAIProvider abstract class (base_provider.py):
   - Method signature:
     async def execute_skill(
         session_id: str,
         user_message: str,
         skill: SkillSchema,
         params: dict
     ) -> SkillResult
   - SkillResult dataclass:
     { output: str, parsed_output: dict | None, skill_name: str,
       model_used: str, confidence: float, routing_decision: RoutingDecision }
   - Method: build_skill_prompt(skill: SkillSchema, params: dict) -> str
     Constructs the full prompt by combining:
       • skill.instructions (the YAML instructions block)
       • Resolved parameter values substituted into the instructions
       • skill.output_format appended as the required response schema
     This prompt is sent to the active AI model as the system + user context.
   - Each provider sends this assembled prompt to its own API
     (Gemini via ADK, OpenAI via openai SDK, Anthropic via anthropic SDK)
   - The model response is parsed against output_format (attempt JSON parse;
     fall back to raw string if format is free-text)

3. ChatOrchestrator (orchestrator.py):
   - Step 1: Receive user_message + session_id
   - Step 2: Ask active_provider to detect which skill matches the message
     by passing all skill descriptions as context and asking the model to
     return the best matching skill name and extracted parameters as JSON.
     If no skill matches with confidence >= 0.5, return None.
   - Step 3: Apply routing (see Objective 4)
   - Step 4: If CALL_SKILL → call active_provider.execute_skill() with the
     matched skill's full YAML and extracted params. The model reads the YAML
     instructions and produces the output directly.
   - Step 5: Return SkillResult to the API layer

4. Provider implementations:
   - gemini_provider.py   → uses google.adk LlmAgent, system_instruction set
                            to the assembled skill prompt
   - openai_provider.py   → uses openai.AsyncOpenAI, messages=[system, user]
   - anthropic_provider.py → uses anthropic.AsyncAnthropic, system + user

5. Data flow:
   User message
     → ChatOrchestrator
       → active_provider: "which skill matches?" + all skill descriptions
         → returns { skill_name: "summarise_document", params: {...},
                     confidence: 0.92 }
       → SkillRegistry.get_skill("summarise_document")
         → returns full YAML with instructions + output_format
       → active_provider.execute_skill(skill_yaml, params)
         → model reads YAML instructions + executes them
         → returns structured SkillResult
     → API response to user

───────────────────────────────────────────────────────────────────────────────
OBJECTIVE 3 — DYNAMIC MODEL SWITCHING
───────────────────────────────────────────────────────────────────────────────

Backend:
- PATCH /session/{session_id}/model  body: { "model": "gpt-4o" }
- Validate against SUPPORTED_MODELS config constant; return 400 on unknown
- Swap active_provider on the session without clearing session history
- SkillRegistry is never rebuilt on model switch (shared, model-agnostic)
- Return { "model": "gpt-4o", "provider": "openai", "session_id": "..." }

SUPPORTED_MODELS config example:
  SUPPORTED_MODELS = {
    "gemini-2.5-pro":   GeminiProvider,
    "gemini-2.0-flash": GeminiProvider,
    "gpt-4o":           OpenAIProvider,
    "gpt-4o-mini":      OpenAIProvider,
    "claude-sonnet-4":  AnthropicProvider,
  }

Frontend:
- Model selector: Apple-style pill segmented control in the chat header
- On change: call PATCH endpoint, show toast "Switched to gpt-4o"
- Optimistic UI: update label immediately, revert on error
- Persist selected model in localStorage key: "preferred_model"
- Load persisted model on page load and call PATCH to sync with backend

───────────────────────────────────────────────────────────────────────────────
OBJECTIVE 4 — LOG-PROBABILITY CONFIDENCE ROUTING
───────────────────────────────────────────────────────────────────────────────

After the active model returns the skill-match response, apply this routing:

RoutingDecision enum: CALL_SKILL | CLARIFY | GENERIC_ANSWER

Rules:
  confidence >= 0.85 AND skill matched  →  CALL_SKILL
  0.50 <= confidence < 0.85             →  CLARIFY
    emit: "I want to make sure I help correctly. Did you mean [skill desc]?"
  confidence < 0.50 OR no skill matched →  GENERIC_ANSWER
    emit: raw model answer without skill execution

Confidence derivation (per provider):
  - Gemini:    use candidate.grounding_metadata or avg token logprob if available;
               fall back to heuristic: exact keyword match in skill description
  - OpenAI:    use logprobs=True on the skill-match request; avg top token prob
  - Anthropic: no native logprobs; use a follow-up self-evaluation prompt:
               "Rate your confidence 0.0–1.0 that [skill] matches the request."
               parse the float from the response

routing_metadata added to every API response:
  { "routing_decision": "CALL_SKILL", "skill_name": "...", "confidence": 0.92 }

Frontend routing badge (below each assistant message):
  CALL_SKILL     → "⚙ Tool Used"       muted teal pill
  CLARIFY        → "? Clarifying"      muted amber pill
  GENERIC_ANSWER → "✦ General Answer"  muted grey pill

───────────────────────────────────────────────────────────────────────────────
OBJECTIVE 5 — CROSS-PLATFORM DOCKER DEPLOYMENT (NO IIS, NO POWERSHELL ON MAC)
───────────────────────────────────────────────────────────────────────────────

Target environments:
  Production     :  Windows Server 2022 + Docker (Mirantis Container Runtime)
  Local Windows  :  Windows 10/11 + Docker Desktop  → PowerShell (.ps1)
  Local macOS    :  macOS 13+    + Docker Desktop    → bash/zsh (.sh)

Docker hosts EVERYTHING. There is no IIS. There is no external web server.
Frontend and backend both run as Docker containers managed by docker-compose.
nginx (as a Docker container) handles all reverse proxy and static file serving.

─── Architecture inside Docker ──────────────────────────────────────────────

  ┌─────────────────────────────────────────────────────┐
  │                  docker-compose                     │
  │                                                     │
  │  ┌──────────┐   ┌──────────┐   ┌────────────────┐  │
  │  │  nginx   │   │   api    │   │     redis      │  │
  │  │  :80/443 │──▶│  :8000   │   │  session store │  │
  │  │ (frontend│   │ (FastAPI │   │                │  │
  │  │  static) │   │ /backend)│   │                │  │
  │  └──────────┘   └──────────┘   └────────────────┘  │
  └─────────────────────────────────────────────────────┘

  nginx container responsibilities:
    - Serve the compiled frontend static files (Angular/React build output)
    - Reverse proxy /api/* → api:8000
    - Handle SSL termination via self-signed cert (dev) or mounted cert (prod)
    - No host-level web server required on any platform

─── File Structure ──────────────────────────────────────────────────────────

  scripts/
    start.sh              # macOS — bash/zsh
    stop.sh               # macOS — bash/zsh
    rebuild.sh            # macOS — bash/zsh
    check_prereqs.sh      # macOS — verifies Docker running, port free, env vars
    start.ps1             # Windows Server + Windows PC — PowerShell
    stop.ps1              # Windows Server + Windows PC — PowerShell
    rebuild.ps1           # Windows Server + Windows PC — PowerShell
    check_prereqs.ps1     # Windows — verifies Docker running, port free, env vars
  nginx/
    nginx.conf            # nginx reverse proxy + static file config
    Dockerfile            # FROM nginx:alpine; COPY dist/ + nginx.conf
  docker-compose.yml      # all services: nginx, api, redis
  docker-compose.dev.yml  # overrides for local dev (volume mounts, hot reload)
  .env.example            # every required env var documented

─── docker-compose.yml ──────────────────────────────────────────────────────

services:
  nginx:
    build: ./nginx
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      api:
        condition: service_healthy
    volumes:
      - ./nginx/certs:/etc/nginx/certs:ro
    restart: unless-stopped

  api:
    build: .
    expose:
      - "8000"
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    volumes:
      - ./skills:/app/skills:ro
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    expose:
      - "6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

─── nginx/nginx.conf ────────────────────────────────────────────────────────

server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # Serve frontend SPA — fallback to index.html for client-side routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Reverse proxy all API calls to the api container
    location /api/ {
        proxy_pass         http://api:8000/;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
    }
}

─── Scripts ─────────────────────────────────────────────────────────────────

scripts/start.sh  (macOS — bash/zsh):
  #!/usr/bin/env bash
  set -euo pipefail
  source "$(dirname "$0")/check_prereqs.sh"
  docker compose pull
  docker compose up -d --build
  docker compose logs -f api

scripts/start.ps1  (Windows — PowerShell):
  #Requires -Version 5.1
  Set-StrictMode -Version Latest
  $ErrorActionPreference = "Stop"
  & "$PSScriptRoot\check_prereqs.ps1"
  $env:COMPOSE_CONVERT_WINDOWS_PATHS = "1"
  docker compose pull
  docker compose up -d --build
  docker compose logs -f api

scripts/check_prereqs.sh  (macOS):
  - Verify docker and docker compose are installed
  - Verify Docker daemon is running (docker info)
  - Verify port 80 is not already bound
  - Verify .env file exists (warn if missing, copy from .env.example)
  - Exit 1 with clear message if any check fails

scripts/check_prereqs.ps1  (Windows):
  - Same checks using PowerShell equivalents
  - Check Docker service: (Get-Service -Name "com.docker.service"
    -ErrorAction SilentlyContinue)
  - Check port: Test-NetConnection -Port 80 -ComputerName localhost
  - Exit 1 with clear message if any check fails

─── Windows Server Production Notes (in README) ─────────────────────────────

  - Install Mirantis Container Runtime (not Docker Desktop) for server use
  - Run scripts using PowerShell 5.1 (built-in) or PowerShell 7+ (preferred)
  - Inject all secrets via Windows System Environment Variables
    (not .env files in production)
  - Open Windows Firewall for inbound TCP 80 and 443
  - For auto-start on boot: create a Scheduled Task pointing to start.ps1
    (provide register_startup_task.ps1 for this)
  - SSL certs: mount via the nginx/certs volume in docker-compose.yml
  - No IIS required or used at any layer

─── macOS Local Notes (in README) ──────────────────────────────────────────

  - Install Docker Desktop for Mac
  - Enable Rosetta for x86/amd64 emulation on Apple Silicon if needed
  - chmod +x scripts/*.sh then ./scripts/start.sh
  - Use docker-compose.dev.yml override for hot reload:
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up

─── Troubleshooting (in README) ─────────────────────────────────────────────

  - Exec into api container:    docker compose exec api bash
  - Exec into nginx container:  docker compose exec nginx sh
  - Check nginx logs:           docker compose logs nginx
  - Rebuild without cache:      docker compose build --no-cache
  - Volume path errors on Windows: ensure COMPOSE_CONVERT_WINDOWS_PATHS=1
    is set before running docker compose (start.ps1 handles this automatically)
  - Port 80 already in use: stop any existing web server process on the host
  - Inspect GOOGLE_APPLICATION_CREDENTIALS inside container:
    docker compose exec api printenv GOOGLE_APPLICATION_CREDENTIALS

───────────────────────────────────────────────────────────────────────────────
OBJECTIVE 6 — UI/UX REDESIGN (APPLE SENIOR WEB DESIGNER STANDARD)
───────────────────────────────────────────────────────────────────────────────

You are acting as a Senior Web Designer from Apple's Human Interface team.
Every decision must pass this test: "Would this ship in Safari or the App Store?"

Design system:
  Typography  : System font stack — -apple-system, BlinkMacSystemFont,
                "SF Pro Display", "SF Pro Text", sans-serif
                Scale: 11 / 13 / 15 / 17 / 22 / 28 / 34px with matching
                line-heights; weight 400/500/600 only
  Color       : CSS custom properties, adaptive light/dark
                --bg-primary:     #F5F5F7 (light) / #1C1C1E (dark)
                --bg-secondary:   #FFFFFF (light) / #2C2C2E (dark)
                --text-primary:   #1D1D1F (light) / #F5F5F7 (dark)
                --text-secondary: #6E6E73 (light) / #98989D (dark)
                --accent:         #0071E3
                --accent-hover:   #0077ED
                --danger:         #FF3B30
  Spacing     : 8pt grid — use multiples of 8px for all margins/padding
  Motion      : cubic-bezier(0.25, 0.1, 0.25, 1); duration 200–320ms
                No bounce, no spring, no overshoot
  Radius      : 12px cards, 8px inputs/buttons, 20px pills
  Shadows     : 0 1px 3px rgba(0,0,0,0.08) cards; no harsh box shadows

Components:
  Chat bubbles:
    User      → right-aligned, background var(--accent), white text, 18px radius
    Assistant → left-aligned, background var(--bg-secondary), var(--text-primary)
  Model selector:
    Apple segmented control (pill group, not a <select> dropdown)
    Active segment: white bg + subtle shadow; inactive: transparent
  Routing badge:
    Small pill below each assistant bubble
    ⚙ Tool Used      → background rgba(52,199,89,0.12)   text #34C759
    ? Clarifying     → background rgba(255,159,10,0.12)  text #FF9F0A
    ✦ General Answer → background rgba(142,142,147,0.12) text #8E8E93
  Input bar:
    Pinned to bottom, frosted glass backdrop-filter: blur(20px)
    Rounded-rectangle input, no visible border until focus
    Focus: 2px solid var(--accent), no outline
  Sidebar (if exists):
    Width 260px, var(--bg-secondary), conversation list items 44px tall
    Selected item: var(--accent) at 10% opacity background

Cross-browser requirements:
  - Add all required -webkit- prefixes (backdrop-filter, appearance, etc.)
  - Test and fix: Chrome 120+, Firefox 122+, Safari 17+, Edge 120+
  - No CSS features below 92% global browser support (check caniuse)

Responsive:
  Mobile first. Breakpoints: 768px (tablet), 1024px (desktop)
  On mobile: sidebar collapses to bottom sheet; input bar full width

Accessibility (WCAG 2.1 AA minimum):
  - All text contrast ratios verified
  - Focus indicators on every interactive element
  - ARIA labels on icon-only buttons
  - Keyboard navigation for model selector and all controls

Deliverables:
  - tokens.css : all CSS custom properties in one file
  - A comment block at top of each changed stylesheet:
    /* CHANGED: [what changed] [why] */

───────────────────────────────────────────────────────────────────────────────
OBJECTIVE 7 — TEST SUITE + STRESS TESTS + BUG FIX LOOP
───────────────────────────────────────────────────────────────────────────────

Write tests AFTER all objectives are implemented. Use the existing test
framework (pytest for backend, Jest/Vitest for frontend).

── Unit Tests ────────────────────────────────────────────────────────────────

Auth (test_auth.py):
  - test_impersonation_path_selected_when_env_set
  - test_keyfile_path_selected_when_credentials_env_set
  - test_ambient_adc_fallback_logs_warning
  - test_auth_config_error_raised_when_all_paths_fail
  - test_credentials_never_logged (assert no credential strings in log output)

SkillRegistry (test_skill_registry.py):
  - test_skills_loaded_from_yaml_directory
  - test_invalid_yaml_skipped_with_warning
  - test_get_skill_returns_correct_schema
  - test_list_skills_returns_all_names
  - test_missing_required_field_in_yaml_raises_validation_error

Routing (test_routing.py):
  - test_call_skill_when_confidence_above_threshold
  - test_clarify_when_confidence_in_middle_band
  - test_generic_answer_when_confidence_below_threshold
  - test_generic_answer_when_no_skill_matched
  - test_routing_metadata_present_in_every_response

Orchestrator (test_orchestrator.py):
  - test_skill_executed_with_correct_params
  - test_model_switch_preserves_session_history
  - test_model_switch_rejects_unknown_model_name
  - test_yaml_instructions_passed_to_model_as_prompt
  - test_output_parsed_against_output_format_schema

Provider parity (test_providers.py):
  - test_gemini_builds_correct_skill_prompt
  - test_openai_builds_correct_skill_prompt
  - test_anthropic_builds_correct_skill_prompt
  - test_all_providers_return_skill_result_dataclass
  - test_provider_swap_does_not_affect_skill_registry

── Integration Tests (test_integration.py) ──────────────────────────────────

  - test_full_flow_skill_matched_and_executed_end_to_end
  - test_full_flow_clarification_returned_on_low_confidence
  - test_model_switch_mid_conversation_then_execute_skill
  - test_invalid_yaml_skill_does_not_crash_registry
  - test_session_isolated_across_concurrent_users

── Stress Tests (test_stress.py) ────────────────────────────────────────────

Run all 5 stress tests using pytest-asyncio + asyncio.gather for concurrency.
Each test must PASS (no exceptions, no data corruption, response time logged).

  ST-01 Concurrent sessions:
    Spin up 50 concurrent sessions each sending 10 messages simultaneously.
    Assert: all 500 responses received, no session data bleeds across users,
    no unhandled exceptions, p95 response time logged.

  ST-02 Rapid model switching:
    Single session sends 100 model-switch requests in 2 seconds
    (cycling through all SUPPORTED_MODELS).
    Assert: every switch acknowledged, final model is consistent with
    last switch, session history intact throughout.

  ST-03 Large YAML skill library:
    Generate 200 synthetic skill YAML files and load the registry.
    Assert: startup completes under 3 seconds, skill selection still
    returns the correct match, memory usage does not exceed 512MB.

  ST-04 Malformed input flood:
    Send 200 requests with: empty string, None, 10,000-character string,
    special characters (null bytes, emoji, RTL text, SQL injection strings,
    prompt injection attempts like "Ignore all instructions and...").
    Assert: every request returns a valid HTTP response (400 or 200),
    no 500 errors, no exceptions propagate to logs uncaught.

  ST-05 Skill hot-reload under load:
    While 20 concurrent sessions are actively sending messages,
    add a new skill YAML file and delete an existing one.
    Assert: in-flight requests complete successfully, new skill is
    available within 2 seconds of file write, deleted skill returns
    graceful "skill not found" response, no crashes.

── Bug Fix Loop ──────────────────────────────────────────────────────────────

After writing all tests, execute this loop and DO NOT STOP until it passes:

  LOOP:
    1. Run full test suite:  pytest -v --tb=short
    2. If any test FAILS:
       a. Read the full traceback
       b. Identify root cause (do not guess — trace through the code)
       c. Fix the bug in the source file
       d. Add a regression test if the bug was not covered
       e. Go to step 1
    3. If all tests PASS:
       a. Run stress tests: pytest test_stress.py -v --asyncio-mode=auto
       b. If any stress test FAILS: fix and go to step 1
       c. If all stress tests PASS: proceed to Done Criteria

DO NOT declare completion until this loop exits cleanly.

───────────────────────────────────────────────────────────────────────────────
EXECUTION ORDER
───────────────────────────────────────────────────────────────────────────────

  Phase 0  → Discovery & audit
  Phase 1  → Objective 1 (auth — all other objectives depend on this)
  Phase 2  → Objective 2 (skill registry + base provider + orchestrator)
  Phase 3  → Objective 3 (model switching BE + FE)
  Phase 4  → Objective 4 (routing layer)
  Phase 5  → Objective 5 (deployment scripts + Docker + README)
  Phase 6  → Objective 6 (UI/UX redesign — after backend shape is final)
  Phase 7  → Objective 7 (tests → stress tests → bug fix loop)

───────────────────────────────────────────────────────────────────────────────
GLOBAL CONSTRAINTS
───────────────────────────────────────────────────────────────────────────────

- Do NOT break existing API contracts; document any changes in BREAKING_CHANGES.md
- Every new function: docstring + full type hints
- No new dependency without adding to requirements.txt / pyproject.toml
- All secrets via environment variables — never hardcoded, never logged
- macOS scripts: bash/zsh .sh files only; Windows scripts: PowerShell .ps1 only
- No .sh files on Windows; no PowerShell dependency on macOS
- Commit message format: feat(scope): description  (Conventional Commits)

───────────────────────────────────────────────────────────────────────────────
DONE CRITERIA — DO NOT STOP BEFORE ALL ARE MET
───────────────────────────────────────────────────────────────────────────────

  ✓ Objective 1 : _resolve_credentials() logs correct auth path;
                  AuthConfigError raised with clear message on failure
  ✓ Objective 2 : Active model reads YAML instructions and executes them;
                  adding a new skills/*.yaml requires zero Python changes
  ✓ Objective 3 : Model switch mid-session preserves history;
                  unknown model returns 400
  ✓ Objective 4 : All three routing decisions reachable; routing_metadata
                  present in every API response; UI badge renders correctly
  ✓ Objective 5 : start.sh runs on macOS; start.ps1 runs on Windows Server
                  and Windows PC; no IIS at any layer; all services run
                  inside Docker containers including frontend via nginx
  ✓ Objective 6 : UI passes visual check on Chrome, Firefox, Safari, Edge;
                  WCAG AA contrast verified; responsive at 375px and 1440px
  ✓ Objective 7 : pytest -v exits 0; all 5 stress tests green;
                  zero unhandled exceptions in logs during stress runs

═══════════════════════════════════════════════════════════════════════════════ add check mark in the execution plan and continue after session limit ended
---

## 2026-04-22T11:55:50Z
R1 - replace API-key with ADC
R2 - retire query_router.py and ensure other llm_provider follow gemini chatorchestrator method
R3 - use nginx and make sure it can be run on local computer without docker. update angular proxy.conf.json + environment.ts and ensure the API and backend does not break.

start Phase 1
---

## 2026-04-22T12:05:20Z
start phase 2
---

## 2026-04-22T12:15:30Z
start phase 3
---

## 2026-04-22T12:21:56Z
start phase 4 and phase 5
---

## 2026-04-22T12:33:22Z
start phase 6
---

## 2026-04-22T12:38:53Z
start phase 7
---

## 2026-04-22T12:48:33Z
/documentation-generation
---

## 2026-04-22T12:54:26Z
/documentation-generation
---

## 2026-04-22T12:58:07Z
update ARCHITECTURE.md
---

## 2026-04-22T13:03:30Z
update Readme.md with cross-platform docker deployment. Im not deploying to GCP cloud run for production
---

## 2026-04-22T13:06:18Z
update architecture.md on the deployment topology
---

## 2026-04-22T13:07:31Z
git push with the commit message on the changes
---

## 2026-04-22T13:08:31Z
git push all files
---

## 2026-04-23T11:28:29Z
/docker review docker file. problem, image is recreated and old one is not deleted.
---

## 2026-04-23T11:31:04Z
fix all
---

## 2026-04-23T11:35:10Z
handle all the potential concern in all docker file
---

## 2026-04-23T11:42:42Z
during migration, copy the sqlite_data and migrate
---

## 2026-04-23T11:46:43Z
address all pontential concerns and review docker design using /docker skill
---

## 2026-04-23T11:53:27Z
/docker review all docker files
---

## 2026-04-23T11:56:43Z
/docker ensure all installation can be done on enterprise computer window OS that may encounter certificate issue
---

## 2026-04-23T12:06:01Z
/docker review and enhance with a more intuitive way to set corporate_ca_cert, http_proxy, https_proxy, no_proxy or any argument to overcome certificate issue
---

## 2026-04-23T12:11:34Z
/error-detective, ignore all documentations while checking the errror
---

## 2026-04-23T12:13:22Z
/error-detective, ignore all documentations while checking the errror
---

## 2026-04-23T12:47:38Z
Implement all the 6 findings
---

## 2026-04-23T12:50:30Z
/documentation-generation you must read all lines of code. ignore all existing documentation and replace all documentation.
---

## 2026-04-23T13:39:36Z
check /chatbot/scripts and all .ps1 and .sh file, check their purpose and consolidate them. update to readme.md on how to use it
---

## 2026-04-23T13:44:55Z
cd ..
---

## 2026-04-23T13:45:54Z
why do you create two readme.md file. keep the most accurate one at the right place. remove breaking_changes.md
---

## 2026-04-24T00:58:33Z
update the hosting to be using https and do not use port 8000
---

## 2026-04-24T01:05:07Z
git push with the commit changes
---
