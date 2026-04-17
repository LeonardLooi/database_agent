# Google ADK + Gemini Voice Agent

> Framework: google-adk (Google Agent Development Kit)
> Models: `gemini-live-2.5-flash-native-audio` (Live), `gemini-2.5-flash-tts-preview` (TTS)
> Python: 3.14 + FastAPI 0.135.2 + asyncio

## Architecture

```
User audio (PCM)
       |
[ADK TranscriptionAgent] --> transcript
                                  |
                     [ADK ResponseAgent] --> response_text
                                  |
                     [ADK SynthesisAgent] --> audio bytes
                                  |
                           FastAPI WebSocket
```

Three ADK agents in a `SequentialAgent` pipeline. Each is independently testable.

---

## 1. ADK FunctionTool — Audio Processing Utilities

```python
import asyncio
import logging
from google.adk.tools import FunctionTool
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
client = genai.Client()


async def transcribe_audio(audio_bytes_hex: str) -> dict:
    """
    ADK FunctionTool: transcribe PCM audio bytes to text via Gemini Live API.

    Args:
        audio_bytes_hex: Hex-encoded PCM audio bytes (16-bit, 16kHz, mono).
                         Hex encoding is used because ADK FunctionTool args are JSON-serializable.

    Returns:
        dict with "transcript" key (str) or "error" key (str) on failure.
    """
    try:
        audio_bytes = bytes.fromhex(audio_bytes_hex)
    except ValueError as exc:
        logger.error("transcribe_audio: invalid hex encoding", exc_info=exc)
        return {"error": "audio_bytes_hex must be valid hex-encoded bytes"}

    if not audio_bytes:
        logger.error("transcribe_audio: empty audio bytes after decoding")
        return {"error": "audio bytes must not be empty"}

    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction=types.Content(
            parts=[types.Part(text="Transcribe the audio exactly. Output only the transcript.")]
        ),
    )

    transcript_parts: list[str] = []

    try:
        async with client.aio.live.connect(
            model="gemini-live-2.5-flash-native-audio",
            config=config,
        ) as session:
            await session.send(
                input=types.AudioChunk(data=audio_bytes, mime_type="audio/pcm;rate=16000"),
            )
            await session.send(end_of_turn=True)

            async for response in session.receive():
                if response.text:
                    transcript_parts.append(response.text)
                if response.server_content and response.server_content.turn_complete:
                    break

    except Exception as exc:
        logger.error("transcribe_audio: Live API failed", exc_info=exc)
        return {"error": f"Transcription failed: {type(exc).__name__}"}

    transcript = "".join(transcript_parts).strip()
    logger.info("transcribe_audio: complete", extra={"transcript_length": len(transcript)})
    return {"transcript": transcript}


async def synthesize_audio(text: str, voice: str = "Aoede") -> dict:
    """
    ADK FunctionTool: synthesize text to speech using Gemini TTS.

    Args:
        text: Text to synthesize.
        voice: Preset voice name (Aoede, Lyra, Orion).

    Returns:
        dict with "audio_hex" key (hex-encoded PCM bytes) or "error" key (str) on failure.
    """
    if not text or not text.strip():
        logger.error("synthesize_audio: empty text")
        return {"error": "text must not be empty"}

    allowed_voices = {"Aoede", "Lyra", "Orion"}
    if voice not in allowed_voices:
        logger.error("synthesize_audio: invalid voice", extra={"voice": voice})
        return {"error": f"voice must be one of {allowed_voices}"}

    def _synthesize() -> bytes:
        _client = genai.Client()
        response = _client.models.generate_content(
            model="gemini-2.5-flash-tts-preview",
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
        data = response.candidates[0].content.parts[0].inline_data.data
        if not data:
            raise RuntimeError("TTS returned empty audio — content may be blocked")
        return data

    try:
        audio_bytes = await asyncio.get_event_loop().run_in_executor(None, _synthesize)
    except Exception as exc:
        logger.error("synthesize_audio: TTS failed", exc_info=exc)
        return {"error": f"Synthesis failed: {type(exc).__name__}"}

    logger.info("synthesize_audio: complete", extra={"audio_bytes": len(audio_bytes)})
    return {"audio_hex": audio_bytes.hex()}


# Register as ADK FunctionTools
transcribe_tool = FunctionTool(func=transcribe_audio)
synthesize_tool = FunctionTool(func=synthesize_audio)
```

---

## 2. ADK Agents — Transcription, Response, Synthesis

```python
import logging
from google.adk.agents import LlmAgent

logger = logging.getLogger(__name__)

# Agent 1: Transcription — calls transcribe_tool, extracts transcript from result
transcription_agent = LlmAgent(
    name="TranscriptionAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a transcription coordinator. "
        "You will receive audio_bytes_hex in the task context. "
        "Call the transcribe_audio tool with that value. "
        "Extract the 'transcript' from the result and store it as 'transcript' in the session state. "
        "If the tool returns an 'error', store it as 'transcription_error' in session state and stop."
    ),
    tools=[transcribe_tool],
    output_key="transcript",
)

# Agent 2: Response — reads transcript from session state, generates text response
response_agent = LlmAgent(
    name="ResponseAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a helpful voice assistant. "
        "Read 'transcript' from session state — this is what the user said. "
        "Generate a concise, natural-sounding response (it will be spoken aloud). "
        "No markdown, no lists, no formatting — plain speech text only. "
        "Store your response as 'response_text' in session state."
    ),
    tools=[],
    output_key="response_text",
)

# Agent 3: Synthesis — calls synthesize_tool with response_text
synthesis_agent = LlmAgent(
    name="SynthesisAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a speech synthesis coordinator. "
        "Read 'response_text' from session state. "
        "Call the synthesize_audio tool with that text and voice='Aoede'. "
        "Store the resulting 'audio_hex' as 'audio_hex' in session state. "
        "If the tool returns an 'error', store it as 'synthesis_error' and stop."
    ),
    tools=[synthesize_tool],
    output_key="audio_hex",
)
```

---

## 3. ADK SequentialAgent Pipeline

```python
import logging
from google.adk.agents import SequentialAgent

logger = logging.getLogger(__name__)

voice_pipeline = SequentialAgent(
    name="VoicePipeline",
    description=(
        "End-to-end voice processing pipeline: "
        "transcribe user audio -> generate response -> synthesize to audio."
    ),
    sub_agents=[transcription_agent, response_agent, synthesis_agent],
)

logger.info(
    "VoicePipeline assembled",
    extra={"agents": ["TranscriptionAgent", "ResponseAgent", "SynthesisAgent"]},
)
```

---

## 4. ADK Runner + FastAPI Integration

```python
import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ADK session service (in-memory for dev; swap for DatabaseSessionService in prod)
session_service = InMemorySessionService()

# ADK runner wraps the pipeline with session management
runner = Runner(
    agent=voice_pipeline,
    app_name="voice-ai-service",
    session_service=session_service,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ADK Voice API starting")
    yield
    logger.info("ADK Voice API shutting down")


app = FastAPI(lifespan=lifespan)


class VoiceTurnRequest(BaseModel):
    audio_hex: str       # Hex-encoded PCM bytes (16-bit, 16kHz, mono)
    session_id: str = "" # Reuse to maintain conversation context


@app.post("/adk/voice/turn")
async def adk_voice_turn(request: VoiceTurnRequest) -> dict:
    """
    Single-turn voice interaction via ADK pipeline.

    Accepts hex-encoded PCM, returns hex-encoded PCM response.
    """
    session_id = request.session_id or str(uuid.uuid4())

    # Validate hex input
    try:
        audio_bytes = bytes.fromhex(request.audio_hex)
    except ValueError as exc:
        logger.warning("Invalid hex audio input", exc_info=exc, extra={"session_id": session_id})
        raise HTTPException(status_code=422, detail="audio_hex must be valid hex-encoded bytes")

    if not audio_bytes:
        raise HTTPException(status_code=422, detail="audio_hex decoded to empty bytes")

    # Ensure session exists
    existing_session = await session_service.get_session(
        app_name="voice-ai-service",
        user_id="voice-user",
        session_id=session_id,
    )
    if not existing_session:
        await session_service.create_session(
            app_name="voice-ai-service",
            user_id="voice-user",
            session_id=session_id,
        )

    # Build ADK message with audio_bytes_hex in context
    message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=f"audio_bytes_hex:{request.audio_hex}")],
    )

    logger.info(
        "ADK voice turn started",
        extra={"session_id": session_id, "audio_bytes": len(audio_bytes)},
    )

    final_state: dict = {}
    response_text_collected: str = ""

    try:
        async for event in runner.run_async(
            user_id="voice-user",
            session_id=session_id,
            new_message=message,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response_text_collected = event.content.parts[0].text or ""

        # Read final session state to get audio_hex output
        final_session = await session_service.get_session(
            app_name="voice-ai-service",
            user_id="voice-user",
            session_id=session_id,
        )
        if final_session and final_session.state:
            final_state = dict(final_session.state)

    except Exception as exc:
        logger.error(
            "ADK voice turn failed",
            exc_info=exc,
            extra={"session_id": session_id},
        )
        raise HTTPException(status_code=502, detail="Voice pipeline processing failed")

    audio_hex = final_state.get("audio_hex", "")
    if not audio_hex:
        synthesis_error = final_state.get("synthesis_error", "unknown")
        logger.error(
            "ADK pipeline produced no audio",
            extra={"session_id": session_id, "synthesis_error": synthesis_error},
        )
        raise HTTPException(status_code=502, detail=f"Audio synthesis failed: {synthesis_error}")

    return {
        "session_id": session_id,
        "transcript": final_state.get("transcript", ""),
        "response_text": final_state.get("response_text", response_text_collected),
        "audio_hex": audio_hex,
    }


@app.websocket("/adk/ws/voice")
async def adk_websocket_voice(websocket: WebSocket) -> None:
    """
    WebSocket voice endpoint using ADK pipeline.

    Protocol:
      Client -> Server: hex-encoded PCM bytes as text message
      Client -> Server: "END" to signal end of turn
      Server -> Client: JSON {"transcript": "...", "response_text": "...", "audio_hex": "..."}
      Server -> Client: "TURN_COMPLETE" after JSON
    """
    import json

    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info("ADK WebSocket voice opened", extra={"session_id": session_id})

    await session_service.create_session(
        app_name="voice-ai-service",
        user_id="voice-user",
        session_id=session_id,
    )

    audio_hex_chunks: list[str] = []

    try:
        while True:
            try:
                text = await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info("ADK WebSocket disconnected", extra={"session_id": session_id})
                break

            if text == "END":
                combined_hex = "".join(audio_hex_chunks)
                audio_hex_chunks.clear()

                if not combined_hex:
                    await websocket.send_text("ERROR:empty_audio")
                    continue

                message = genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text=f"audio_bytes_hex:{combined_hex}")],
                )

                try:
                    async for event in runner.run_async(
                        user_id="voice-user",
                        session_id=session_id,
                        new_message=message,
                    ):
                        pass  # Process all events

                    final_session = await session_service.get_session(
                        app_name="voice-ai-service",
                        user_id="voice-user",
                        session_id=session_id,
                    )
                    state = dict(final_session.state) if final_session and final_session.state else {}

                    if not state.get("audio_hex"):
                        await websocket.send_text(f"ERROR:{state.get('synthesis_error', 'no_audio')}")
                        continue

                    await websocket.send_text(json.dumps({
                        "transcript": state.get("transcript", ""),
                        "response_text": state.get("response_text", ""),
                        "audio_hex": state.get("audio_hex", ""),
                    }))
                    await websocket.send_text("TURN_COMPLETE")

                except Exception as exc:
                    logger.error(
                        "ADK pipeline error in WebSocket",
                        exc_info=exc,
                        extra={"session_id": session_id},
                    )
                    await websocket.send_text("ERROR:pipeline_failed")

            else:
                # Accumulate hex audio chunks
                audio_hex_chunks.append(text)

    except Exception as exc:
        logger.error("ADK WebSocket error", exc_info=exc, extra={"session_id": session_id})
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
        raise
```

---

## 5. End-to-End Example Flow

```
1. User presses microphone in browser/Flutter app
2. Client captures PCM audio, hex-encodes it, sends via WebSocket
3. Client sends "END" to signal turn complete
4. FastAPI receives accumulated hex chunks, combines them
5. ADK Runner invokes VoicePipeline:
   a. TranscriptionAgent: calls transcribe_audio tool -> stores "transcript" in session state
   b. ResponseAgent: reads "transcript" -> generates response -> stores "response_text"
   c. SynthesisAgent: calls synthesize_audio tool -> stores "audio_hex" in session state
6. FastAPI reads session state, extracts audio_hex
7. FastAPI sends JSON {"transcript", "response_text", "audio_hex"} over WebSocket
8. Client decodes hex back to bytes, plays through audio output
9. Session_id persists for multi-turn conversation memory
```

---

## 6. ADK Session Persistence for Multi-Turn

```python
# For production: replace InMemorySessionService with DatabaseSessionService
# so conversation context survives restarts.

# from google.adk.sessions import DatabaseSessionService
#
# session_service = DatabaseSessionService(
#     db_url=os.environ["DATABASE_URL"]  # PostgreSQL connection string
# )

# For now, InMemorySessionService works for single-instance deployments.
# Each session_id maintains conversation history automatically.
```

---

## 7. Error Handling Reference

| Scenario | Agent | Handling |
|----------|-------|----------|
| Empty audio bytes | TranscriptionAgent | Tool returns `{"error": "..."}` -> agent stores `transcription_error`, stops |
| Live API rate limit | transcribe_audio tool | Returns `{"error": "Transcription failed: ResourceExhausted"}` — caller must retry |
| TTS content blocked | synthesize_audio tool | Returns `{"error": "Synthesis failed: PermissionDenied"}` -> agent stores `synthesis_error` |
| ADK runner timeout | FastAPI | Catch `asyncio.TimeoutError`, return HTTP 504 |
| Session not found | FastAPI | Create session before running, never assume it exists |

```python
import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_with_timeout(runner, user_id: str, session_id: str, message, timeout: float = 30.0):
    """Run ADK pipeline with timeout guard."""
    try:
        async with asyncio.timeout(timeout):
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=message,
            ):
                pass
    except asyncio.TimeoutError:
        logger.error(
            "ADK pipeline timed out",
            extra={"session_id": session_id, "timeout": timeout},
        )
        raise  # Let FastAPI catch and return 504
    except Exception as exc:
        logger.error("ADK pipeline failed", exc_info=exc, extra={"session_id": session_id})
        raise
```

---

## 8. ADK vs LangGraph Decision Guide

| Concern | Use ADK | Use LangGraph |
|---------|---------|---------------|
| Session management built-in | Yes | Manual |
| Memory / artifacts | Yes | Manual |
| Agent reuse / composition | Yes | Yes |
| Fine-grained state control | Limited | Full |
| Existing LangChain tools | No | Yes |
| Google Cloud deployment (Agent Engine) | Yes | No |
| Complex conditional branching | Limited | Yes |
| Debug via ADK web UI | Yes | No |

**Rule:** Use ADK when you need session management, memory, or plan to deploy to Agent Engine. Use LangGraph when you need precise state control or existing LangChain tools.
