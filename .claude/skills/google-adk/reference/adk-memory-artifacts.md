# ADK Memory and Artifact Services

## 1. Memory Service Setup

`InMemoryMemoryService` stores session memories in process memory — suitable for
development and testing. Pass it to `Runner` via `memory_service`.

```python
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService

memory_service = InMemoryMemoryService()

runner = Runner(
    app_name="my-app",
    agent=agent,
    session_service=InMemorySessionService(),
    memory_service=memory_service,
)
```

**Production note:** Replace `InMemoryMemoryService` with `VertexAiRagMemoryService`
for persistent, scalable storage. `VertexAiRagMemoryService` requires a Vertex AI
RAG corpus to be configured in your GCP project before use.

---

## 2. Built-in Memory Tools

Add `load_memory` and/or `preload_memory` to the agent's `tools` list.
ADK injects the memory service automatically — no extra wiring required.

```python
from google.adk import Agent
from google.adk.tools import load_memory, preload_memory

agent = Agent(
    name="memory_agent",
    model="gemini-3.1-flash",
    instruction="Use your memory to provide personalized responses.",
    tools=[load_memory, preload_memory],
)
```

- `load_memory` — retrieves relevant memories on demand during a conversation turn.
- `preload_memory` — loads memories at the start of a turn, before the model runs.

---

## 3. Custom Memory Search Tool

Use `tool_context.search_memory(query)` to run a semantic search against the
configured memory service. Iterate `results.memories` to access each entry.

```python
from google.adk.tools import ToolContext

async def search_past_conversations(query: str, tool_context: ToolContext) -> dict:
    """Search previous conversation history for relevant information.

    Args:
        query: Natural language query describing what to look for.
        tool_context: Injected by ADK — do not pass manually.

    Returns:
        A dict with 'memories' list, each item having 'content' str.
    """
    results = await tool_context.search_memory(query)
    memories = []
    for memory in results.memories:
        memories.append({"content": memory.content})
    return {"query": query, "memories": memories, "count": len(memories)}
```

---

## 4. Saving Sessions to Memory

After a conversation ends, persist the session so future searches can find it.
Call `add_session_to_memory` once per completed session — not per turn.

```python
# After the conversation loop completes:
await memory_service.add_session_to_memory(session)
```

Retrieve the `session` object from `runner.session_service.get_session(...)` or
track it from the initial `create_session` call. Sessions not added to memory are
not searchable in future conversations.

---

## 5. Artifact Service Setup

`InMemoryArtifactService` holds artifact bytes in memory (dev/test).
`FileArtifactService` persists artifacts to disk (production).
Pass either to `Runner` via `artifact_service`.

```python
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService, FileArtifactService

# Development
artifact_service = InMemoryArtifactService()

# Production
artifact_service = FileArtifactService(base_dir="/tmp/artifacts")

runner = Runner(
    app_name="my-app",
    agent=agent,
    session_service=InMemorySessionService(),
    artifact_service=artifact_service,
)
```

---

## 6. Save Artifact Tool

Artifacts are stored as `types.Part` objects. Build a `Part` with `inline_data`
containing the MIME type and raw bytes. `save_artifact` returns an integer version
number that increments on each save.

```python
from google.adk.tools import ToolContext
from google.genai import types

async def save_image(
    filename: str, image_bytes: bytes, mime_type: str, tool_context: ToolContext
) -> dict:
    """Save binary image data as a named artifact.

    Args:
        filename: Name to store the artifact under (e.g. 'chart.png').
        image_bytes: Raw binary content of the image.
        mime_type: MIME type string (e.g. 'image/png', 'image/jpeg').
        tool_context: Injected by ADK — do not pass manually.

    Returns:
        A dict with 'filename' str and 'version' int.
    """
    artifact = types.Part(
        inline_data=types.Blob(mime_type=mime_type, data=image_bytes)
    )
    version = await tool_context.save_artifact(filename, artifact)
    return {"filename": filename, "version": version}
```

---

## 7. Load Artifact Tool

`load_artifact` returns a `types.Part` if the artifact exists, or `None` if not
found. Always check for `None` before accessing fields.

```python
from google.adk.tools import ToolContext

async def load_image(filename: str, tool_context: ToolContext) -> dict:
    """Load a previously saved artifact by filename.

    Args:
        filename: Name of the artifact to retrieve.
        tool_context: Injected by ADK — do not pass manually.

    Returns:
        A dict with 'found' bool, 'filename' str, 'mime_type' str,
        and 'size_bytes' int when found.
    """
    artifact = await tool_context.load_artifact(filename)
    if artifact is None:
        return {"found": False, "filename": filename}
    return {
        "found": True,
        "filename": filename,
        "mime_type": artifact.inline_data.mime_type,
        "size_bytes": len(artifact.inline_data.data),
    }
```

---

## 8. List Artifacts Tool

`list_artifacts` returns a `list[str]` of all artifact filenames stored in the
current session.

```python
from google.adk.tools import ToolContext

async def list_saved_files(tool_context: ToolContext) -> dict:
    """List all artifact filenames saved in this session.

    Args:
        tool_context: Injected by ADK — do not pass manually.

    Returns:
        A dict with 'filenames' list[str] and 'count' int.
    """
    filenames = await tool_context.list_artifacts()
    return {"filenames": filenames, "count": len(filenames)}
```

---

## 9. Memory vs Artifacts Reference Table

| Feature | Memory Service | Artifact Service |
|---------|---------------|-----------------|
| Purpose | Long-term semantic retrieval across sessions | Binary file storage within/across sessions |
| Dev implementation | `InMemoryMemoryService` | `InMemoryArtifactService` |
| Prod implementation | `VertexAiRagMemoryService` | `FileArtifactService(base_dir=...)` |
| Access via ToolContext | `tool_context.search_memory(query)` | `tool_context.save_artifact` / `load_artifact` / `list_artifacts` |
| Persistence model | Session-based — call `add_session_to_memory` to persist | Versioned by filename — each save increments version |
| Retrieval method | Semantic similarity search | Exact filename lookup |
| Data type | Text / conversation content | Binary blobs (`types.Part` with `inline_data`) |

---

## Imports Summary

```python
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.artifacts import InMemoryArtifactService, FileArtifactService
from google.adk.tools import ToolContext, load_memory, preload_memory
from google.genai import types
```
