# Gemini Provider Setup

Reference for configuring Gemini Live API (real-time STT) and Gemini TTS as primary voice providers.

---

## SDK Installation

```bash
# CORRECT — use google-genai
uv add "google-genai>=1.0.0"

# WRONG — never use this
# pip install google-generativeai  ← deprecated, different API surface
```

The `google-generativeai` package is the legacy SDK. `google-genai` is the current, actively maintained SDK with Live API support. They are not interchangeable.

---

## Authentication

```python
import os
from google import genai

# Option 1: API key (development)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Option 2: Application Default Credentials (GCP production)
# Set GOOGLE_APPLICATION_CREDENTIALS env var, then:
client = genai.Client()
```

**Never hardcode API keys.** Load from environment via pydantic-settings:

```python
from pydantic_settings import BaseSettings

class VoiceEngineConfig(BaseSettings):
    gemini_api_key: str
    gemini_live_model: str = "gemini-live-2.5-flash-native-audio"
    gemini_tts_model: str = "gemini-2.5-flash-tts-preview"
    gemini_tts_voice: str = "Aoede"

    model_config = {"env_file": ".env", "extra": "ignore"}
```

---

## Gemini Live API — Real-time STT + S2S

### Model

```
gemini-live-2.5-flash-native-audio
```

### Protocol

WebSocket (raw audio bytes). **Polling does not work with Live API.**

### Audio Format Requirements (Input — user audio)

| Parameter | Value |
|-----------|-------|
| Format | Linear PCM (raw bytes) |
| Sample rate | 16,000 Hz |
| Channels | 1 (mono) |
| Bit depth | 16-bit signed little-endian |
| Chunk size | 1024–4096 bytes (small chunks for low latency) |

### Audio Format Requirements (Output — Gemini response audio)

| Parameter | Value |
|-----------|-------|
| Format | Linear PCM |
| Sample rate | 24,000 Hz (Live API default output) |
| Channels | 1 (mono) |
| Bit depth | 16-bit signed little-endian |

### Live API WebSocket Setup

```python
import asyncio
import structlog
from google import genai
from google.genai import types

log = structlog.get_logger()

async def connect_gemini_live(
    client: genai.Client,
    model: str,
    system_instruction: str,
) -> genai.live.AsyncSession:
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],  # or ["TEXT"] for text-only
        system_instruction=system_instruction,
        # Native barge-in is enabled by default — no extra config needed
    )
    session = await client.aio.live.connect(model=model, config=config)
    return session
```

### Sending Audio Chunks

```python
async def send_audio_chunk(session: genai.live.AsyncSession, chunk: bytes) -> None:
    """Send a raw PCM audio chunk to Gemini Live API."""
    await session.send_realtime_input(
        types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
    )
```

### Receiving Transcriptions and Audio

```python
async def receive_responses(session: genai.live.AsyncSession, output_queue: asyncio.Queue) -> None:
    """Receive streaming responses from Gemini Live API."""
    async for response in session:
        if response.server_content:
            content = response.server_content
            if content.model_turn:
                for part in content.model_turn.parts:
                    if part.text:
                        await output_queue.put({"type": "transcript", "text": part.text})
                    if part.inline_data:
                        await output_queue.put({"type": "audio", "data": part.inline_data.data})
            if content.turn_complete:
                await output_queue.put({"type": "turn_complete"})
```

### Native Barge-in (Interrupt) Support

Gemini Live API handles interrupts natively. When the user speaks during bot audio playback, Gemini automatically:
1. Detects the user's voice (VAD — Voice Activity Detection)
2. Stops generating the current response
3. Begins processing the new user input

You still need to stop sending the bot's audio to the client on interrupt — see `interrupt-handling.md`.

```python
# No special config needed — barge-in is enabled by default
# Just stop reading from the audio output queue when interrupted
```

### Session Timeout and Reconnect

Gemini Live sessions expire after approximately 10 minutes of inactivity or 30 minutes total.

```python
import asyncio
import structlog
from google import genai

log = structlog.get_logger()

class GeminiLiveSessionManager:
    def __init__(self, client: genai.Client, model: str, system_instruction: str):
        self._client = client
        self._model = model
        self._system_instruction = system_instruction
        self._session: genai.live.AsyncSession | None = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

    async def get_session(self) -> genai.live.AsyncSession:
        if self._session is None:
            await self._connect()
        return self._session

    async def _connect(self) -> None:
        backoff = 1.0
        for attempt in range(self._max_reconnect_attempts):
            try:
                config = types.LiveConnectConfig(
                    response_modalities=["AUDIO"],
                    system_instruction=self._system_instruction,
                )
                self._session = await self._client.aio.live.connect(
                    model=self._model, config=config
                )
                self._reconnect_attempts = 0
                log.info("gemini_live_connected", model=self._model)
                return
            except Exception as exc:
                log.error("gemini_live_connect_failed", attempt=attempt, error=str(exc))
                if attempt < self._max_reconnect_attempts - 1:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30.0)
                else:
                    raise

    async def handle_session_expired(self) -> None:
        log.warning("gemini_live_session_expired_reconnecting")
        self._session = None
        await self._connect()
```

---

## Gemini TTS Models

### Model Selection

| Model | Use When | Notes |
|-------|----------|-------|
| `gemini-2.5-flash-tts-preview` | Default — fast, low latency | Good quality, low cost |
| `gemini-2.5-pro-tts-preview` | High fidelity required | Slower, higher cost |

### Preset Voices

Gemini TTS includes preset voices. Common options: `Aoede`, `Lyra`, `Orion`. Total 5–8 presets (check `ai.google.dev` for current list).

### Basic TTS Request

```python
import asyncio
import structlog
from google import genai
from google.genai import types

log = structlog.get_logger()

async def synthesize_speech(
    client: genai.Client,
    text: str,
    model: str = "gemini-2.5-flash-tts-preview",
    voice: str = "Aoede",
) -> bytes:
    """
    Synthesize text to PCM audio bytes using Gemini TTS.
    Returns raw Linear PCM audio at 24kHz mono 16-bit.
    """
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                ),
            ),
        )
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        log.info("tts_synthesized", chars=len(text), model=model, voice=voice)
        return audio_data
    except Exception as exc:
        log.error("tts_synthesis_failed", text_preview=text[:50], error=str(exc), exc_info=True)
        raise
```

### Style Control via Natural Language

```python
# Control speaking style through the text prompt itself
styled_text = "Say in a calm, reassuring tone: Everything is going to be fine."
audio = await synthesize_speech(client, styled_text)

# Multi-speaker (for dialogue synthesis)
dialogue = """
TTS the following conversation:
Speaker 1: Hello, how can I help you today?
Speaker 2: I need assistance with my account.
"""
```

---

## Rate Limits and Error Codes

| Limit | Value (as of 2026-03) |
|-------|----------------------|
| Live API — concurrent sessions | Varies by tier; check Google AI Studio quota |
| Live API — session duration | ~30 min max per session |
| TTS — requests per minute | ~60 RPM on free tier |
| TTS — characters per minute | Check current quota at console.cloud.google.com |

### Common Error Codes

| Error | Cause | Fix |
|-------|-------|-----|
| `INVALID_ARGUMENT` audio format | Wrong sample rate or encoding | Verify 16kHz PCM for input, check `mime_type` |
| `SESSION_EXPIRED` | Live session >10–30 min | Implement reconnect (see `GeminiLiveSessionManager`) |
| `RESOURCE_EXHAUSTED` | Rate limit hit | Implement exponential backoff; check quota |
| `UNAUTHENTICATED` | Bad or missing API key | Check `GEMINI_API_KEY` env var |
| WebSocket disconnection | Network or server issue | Reconnect with backoff |

---

## Environment Variables

```bash
# .env
GEMINI_API_KEY=your-api-key-here
GEMINI_LIVE_MODEL=gemini-live-2.5-flash-native-audio
GEMINI_TTS_MODEL=gemini-2.5-flash-tts-preview
GEMINI_TTS_VOICE=Aoede
```
