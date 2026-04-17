---
name: voice-ai-development
description: "Gemini voice AI development — real-time voice streaming with Gemini Live API (WebSocket), text-to-speech with Gemini TTS models, LangGraph voice agent pipelines, and Google ADK voice agents. Use when building voice assistants, real-time audio streaming, TTS synthesis, or multimodal voice applications."
allowed-tools: Bash, Read, Write, Edit, WebFetch
metadata:
  triggers: Gemini Live API, Gemini TTS, voice AI, real-time voice, audio streaming, WebSocket audio, barge-in, text-to-speech, TTS, gemini-live-2.5-flash-native-audio, gemini-2.5-pro-tts-preview, gemini-2.5-flash-tts-preview, voice agent, speech synthesis, voice assistant, multimodal voice
  related-skills: gemini-api-dev, google-adk, agentic-ai-dev, python-dev
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

## Iron Law

**ALWAYS USE WEBSOCKETS FOR LIVE API — NEVER POLLING; ALWAYS USE gemini-live-2.5-flash-native-audio FOR REAL-TIME, gemini-2.5-pro-tts-preview OR gemini-2.5-flash-tts-preview FOR TTS**

# Voice AI Development — Gemini Live API + TTS

## When to Use This Skill

| Use Case | This Skill | gemini-api-dev skill |
|----------|-----------|---------------------|
| Real-time voice streaming | ✅ | ❌ |
| Barge-in / interrupt detection | ✅ | ❌ |
| Sub-second voice latency (<600ms) | ✅ | ❌ |
| Text-to-speech synthesis | ✅ | ❌ |
| Multi-speaker podcast/dialogue TTS | ✅ | ❌ |
| Voice + camera multimodal | ✅ | ❌ |
| LangGraph voice agent pipeline | ✅ | ❌ |
| ADK voice agent | ✅ | ❌ |
| Standard text/multimodal calls | ❌ | ✅ |

## Models

### Live API (Real-time Voice)
- **`gemini-live-2.5-flash-native-audio`** — Primary model for real-time voice. Sub-second latency (~600ms). Barge-in, affective dialogue, multimodal (audio + camera). **Always use this for real-time.**

### TTS Models
- **`gemini-2.5-pro-tts-preview`** — Highest fidelity. Use for audiobooks, podcasts, production voiceovers.
- **`gemini-2.5-flash-tts-preview`** — Faster and cheaper. Use for real-time TTS responses, e-learning, notifications.

### TTS Model Selection Guide

| Scenario | Model |
|----------|-------|
| Production audiobook / podcast | `gemini-2.5-pro-tts-preview` |
| Real-time assistant reply | `gemini-2.5-flash-tts-preview` |
| Multi-speaker dialogue | Either (flash cheaper at scale) |
| Voice quality is demo-critical | `gemini-2.5-pro-tts-preview` |

## Preset Voices (Live API)

Available: **Aoede**, **Lyra**, **Orion** (5–8 distinct steerable voices total)

- Style transfer: can mimic speaking patterns and emotions
- Cannot clone custom/external voices

## SDK

```bash
# Python — ALWAYS use google-genai, NEVER google-generativeai (deprecated)
uv add google-genai

# Verify
python -c "import google.genai; print(google.genai.__version__)"
```

## Quick Scaffold

### Live API — Real-time Voice (FastAPI WebSocket)
```python
# See reference/gemini-live-api.md for full implementation
from google import genai
from google.genai import types
import asyncio

client = genai.Client()

async def stream_voice():
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
    )
    async with client.aio.live.connect(
        model="gemini-live-2.5-flash-native-audio",
        config=config
    ) as session:
        await session.send(input="Hello, how can I help?", end_of_turn=True)
        async for response in session.receive():
            if response.data:
                yield response.data  # raw PCM bytes
```

### TTS — Single Speaker
```python
# See reference/gemini-tts.md for full implementation
from google import genai

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash-tts-preview",
    contents="Say this in a warm, friendly tone: Hello and welcome!",
    config={"response_modalities": ["AUDIO"]},
)
audio_bytes = response.candidates[0].content.parts[0].inline_data.data
```

## Process

1. **Choose modality** — real-time streaming (Live API) vs batch TTS (TTS models)
2. **Load reference files** — `gemini-live-api.md` for streaming; `gemini-tts.md` for TTS
3. **Pick framework** — LangGraph (`voice-langgraph-integration.md`) or ADK (`voice-adk-integration.md`)
4. **Implement WebSocket transport** — FastAPI WebSocket endpoint proxies audio bytes bidirectionally
5. **Add error handling** — connection drops, rate limits, audio format validation (no silent failures)
6. **Test audio pipeline** — verify raw PCM bytes received and playable before adding agent logic
7. **Dispatch reviewers** — `security-reviewer` (API key handling), `code-reviewer` (error path coverage)

## Key Patterns

| Pattern | When | Reference |
|---------|------|-----------|
| WebSocket proxy to Live API | Real-time browser-to-Gemini audio | `gemini-live-api.md` |
| Barge-in handling | User interrupts assistant mid-speech | `gemini-live-api.md` |
| Multi-speaker TTS | Podcast/dialogue with named speakers | `gemini-tts.md` |
| LangGraph voice StateGraph | Transcribe → LLM → Synthesize pipeline | `voice-langgraph-integration.md` |
| ADK SequentialAgent voice | ADK-based transcription/response/synthesis agents | `voice-adk-integration.md` |
| Style control via natural language | "whispered mysterious tone", "enthusiastic Australian accent" | `gemini-tts.md` |
| Mid-sentence language switch | Multilingual TTS (70+ languages) | `gemini-tts.md` |
| Multimodal voice + camera | Live API audio + video frames | `gemini-live-api.md` |

## Documentation Sources

| Source | URL | Purpose |
|--------|-----|---------|
| Live API overview | `https://ai.google.dev/gemini-api/docs/live.md.txt` | WebSocket protocol, connection lifecycle |
| TTS overview | `https://ai.google.dev/gemini-api/docs/speech.md.txt` | TTS models, voice config, multi-speaker |
| Audio understanding | `https://ai.google.dev/gemini-api/docs/audio.md.txt` | Sending audio to Gemini |
| Models reference | `https://ai.google.dev/gemini-api/docs/models.md.txt` | Current model IDs and capabilities |
| Doc index | `https://ai.google.dev/gemini-api/docs/llms.txt` | Discover all doc pages |
| google-genai Python SDK | `https://googleapis.github.io/python-genai/` | SDK API reference |

## Reference Files

| File | Contents |
|------|----------|
| `reference/gemini-live-api.md` | WebSocket setup, audio streaming, barge-in, multimodal, FastAPI proxy, LangGraph node |
| `reference/gemini-tts.md` | Single/multi-speaker TTS, style control, language switching, streaming TTS, FastAPI endpoint |
| `reference/voice-langgraph-integration.md` | LangGraph StateGraph: transcribe → LLM → synthesize, FastAPI streaming endpoint |
| `reference/voice-adk-integration.md` | ADK LlmAgent + SequentialAgent voice pipeline, FunctionTool audio processing, FastAPI runner |

## Common Commands

```bash
# Install SDK
uv add google-genai

# Set API key (get from aistudio.google.com)
export GOOGLE_API_KEY=your_key_here

# Run FastAPI voice server
uvicorn main:app --reload --port 8000

# Test WebSocket connection (requires wscat: npm install -g wscat)
wscat -c ws://localhost:8000/ws/voice

# Test TTS endpoint
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "model": "gemini-2.5-flash-tts-preview"}' \
  --output output.wav

# Check SDK version
python -c "import google.genai; print(google.genai.__version__)"
```

## Error Handling

```
Connection drop (Live API WebSocket):
  → Catch asyncio.CancelledError and websockets.exceptions.ConnectionClosed
  → Log error with session context
  → Re-raise — do NOT silently reconnect without user awareness

Rate limit (429):
  → Log warning with retry-after header value
  → Implement exponential backoff (1s, 2s, 4s, max 32s)
  → Raise RateLimitError after max retries

Audio format error:
  → Validate input: PCM 16-bit, 16kHz, mono for Live API
  → Log format mismatch with received vs expected
  → Raise AudioFormatError — do NOT attempt to play malformed audio

Content policy block:
  → Log blocked content category (never log the content itself)
  → Return error state to caller — do NOT return silence as if successful

API key / auth (401):
  → Check GOOGLE_API_KEY env var is set
  → Log "API key missing or invalid" — never log the key value
  → Raise AuthenticationError immediately — no retry
```

## Post-Code Review

After writing Gemini voice integration code, dispatch:
- `security-reviewer` — API key handling, no keys in code, audio data sanitization
- `code-reviewer` — WebSocket lifecycle, error path coverage, no silent failures
