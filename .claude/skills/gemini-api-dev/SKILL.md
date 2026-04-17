---
name: gemini-api-dev
description: "Direct Gemini API development with google-genai (Python) and @google/genai (TypeScript). Use when building multimodal applications, function calling, structured output, context caching, embeddings, or code execution with Gemini models — without the ADK framework overhead."
allowed-tools: Bash, Read, Write, Edit, WebFetch
metadata:
  triggers: Gemini API, google-genai, @google/genai, multimodal, Gemini embeddings, context caching, code execution sandbox, Gemini function calling, Gemini structured output, direct Gemini, gemini-3.1
  related-skills: google-adk, agentic-ai-dev, python-dev, nestjs-api
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

## Iron Law

**ALWAYS FETCH CURRENT API DOCS BEFORE WRITING CODE — fetch `https://ai.google.dev/gemini-api/docs/llms.txt` first, then the specific capability page. Never generate Gemini API calls from memory; the API evolves rapidly.**

# Gemini API Development — Direct API (google-genai / @google/genai)

## When to Use This Skill vs google-adk

| Use Case | This Skill | google-adk skill |
|----------|-----------|-----------------|
| Direct model API calls | ✅ | ❌ |
| Multimodal (image/audio/video) | ✅ | Partial |
| Embeddings API | ✅ | ❌ |
| Context caching | ✅ | ❌ |
| Code execution sandbox | ✅ | ❌ |
| Building structured AI agents | ❌ | ✅ |
| Session management / memory | ❌ | ✅ |
| Multi-agent orchestration | ❌ | ✅ |

## Current Models (as of 2026-03-15)

- `gemini-3.1-flash` — 1M tokens, fast, balanced, multimodal. **Default for most tasks.**
- `gemini-3.1-pro` — 1M tokens, complex reasoning, coding, research
- `gemini-3.1-pro-image` — Image generation and editing

> **Legacy models are deprecated:** `gemini-2.5-*`, `gemini-2.0-*`, `gemini-1.5-*` — do not use.

## SDKs

- **Python**: `google-genai` — `uv add google-genai`
- **TypeScript/NestJS**: `@google/genai` — `npm install @google/genai`

> **Legacy SDKs are deprecated:** `google-generativeai` (Python) and `@google/generative-ai` (JS) — do not use.

## Quick Start

### Python
```python
from google import genai

client = genai.Client()  # uses GOOGLE_API_KEY env var
response = client.models.generate_content(
    model="gemini-3.1-flash",
    contents="Explain quantum computing"
)
print(response.text)
```

### TypeScript (NestJS)
```typescript
import { GoogleGenAI } from "@google/genai";

const ai = new GoogleGenAI({});  // uses GOOGLE_API_KEY env var
const response = await ai.models.generateContent({
  model: "gemini-3.1-flash",
  contents: "Explain quantum computing"
});
console.log(response.text);
```

## Key Capabilities

| Capability | When to Use | Doc Page |
|-----------|-------------|----------|
| Text generation | Chat, completion, summarization | `text-generation.md.txt` |
| Multimodal | Process images, audio, video, documents | `image-understanding.md.txt` |
| Function calling | Let the model invoke your functions | `function-calling.md.txt` |
| Structured output | Generate valid JSON matching schema | `structured-output.md.txt` |
| Code execution | Run Python in sandboxed environment | fetch from llms.txt |
| Context caching | Cache large contexts for cost efficiency | fetch from llms.txt |
| Embeddings | Semantic search, similarity | `embeddings.md.txt` |

## Documentation Sources

**Always fetch before writing code** — the Gemini API evolves rapidly; never rely on memory.

| Source | URL | Purpose |
|--------|-----|---------|
| Doc index | `https://ai.google.dev/gemini-api/docs/llms.txt` | Discover all available doc pages |
| Models | `https://ai.google.dev/gemini-api/docs/models.md.txt` | Current model IDs and capabilities |
| Function calling | `https://ai.google.dev/gemini-api/docs/function-calling.md.txt` | Tool use patterns |
| Structured output | `https://ai.google.dev/gemini-api/docs/structured-output.md.txt` | JSON schema output |
| Embeddings | `https://ai.google.dev/gemini-api/docs/embeddings.md.txt` | Embedding API |
| Text generation | `https://ai.google.dev/gemini-api/docs/text-generation.md.txt` | Generation parameters |
| Image understanding | `https://ai.google.dev/gemini-api/docs/image-understanding.md.txt` | Multimodal inputs |
| SDK migration | `https://ai.google.dev/gemini-api/docs/migrate.md.txt` | Migrate from legacy SDKs |
| REST API spec | `https://generativelanguage.googleapis.com/$discovery/rest?version=v1beta` | Authoritative API schema |

## Common Commands

```bash
# Python setup
uv add google-genai

# TypeScript setup
npm install @google/genai

# Set API key (get from Google AI Studio: aistudio.google.com)
export GOOGLE_API_KEY=your_key_here

# Verify SDK version
python -c "import google.genai; print(google.genai.__version__)"
node -e "const {GoogleGenAI}=require('@google/genai'); console.log('ok')"
```

## Error Handling

> Fetch `https://ai.google.dev/gemini-api/docs/error-codes.md.txt` for current error code reference.

**Rate limits (429):** Implement exponential backoff — do not retry immediately.
**Invalid API key (401):** Check `GOOGLE_API_KEY` env var — never hardcode keys.
**Model not found:** Verify model ID against `models.md.txt` — model names change between releases.
**Payload too large:** Check 2MB limit for inline data; use File API for larger inputs.

```python
# Python — retry with backoff on rate limit
import time
from google.api_core import retry
from google import genai

client = genai.Client()

@retry.Retry(predicate=retry.if_transient_error)
def generate_with_retry(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-3.1-flash",
        contents=prompt,
    )
    return response.text
```

## Post-Code Review

After writing Gemini API integration code, dispatch:
- `security-reviewer` — API key handling, no keys in code, input sanitization before sending to model
- `code-reviewer` — general quality, error handling completeness
