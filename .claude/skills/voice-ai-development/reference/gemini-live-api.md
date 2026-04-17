# Gemini Live API — Real-time Voice Streaming

> Model: `gemini-live-2.5-flash-native-audio`
> Protocol: WebSocket (bidirectional audio bytes)
> SDK: `google-genai` (Python) — NEVER `google-generativeai` (deprecated)

## Overview

The Gemini Live API enables sub-second latency (~600ms) real-time voice conversations via WebSocket streaming. Key features:
- **Barge-in**: user can interrupt while the model is speaking
- **Affective dialogue**: emotion-aware responses
- **Multimodal**: simultaneous audio + camera/video input
- **Raw audio bytes**: PCM 16-bit, 16kHz, mono input; PCM output

---

## 1. WebSocket Connection Setup

```python
import asyncio
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

client = genai.Client()  # reads GOOGLE_API_KEY from env

LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name="Aoede"  # Options: Aoede, Lyra, Orion
            )
        )
    ),
    system_instruction=types.Content(
        parts=[types.Part(text="You are a helpful voice assistant. Be concise.")]
    ),
)


async def connect_live_session():
    """Open a Live API session. Caller must use as async context manager."""
    return client.aio.live.connect(
        model="gemini-live-2.5-flash-native-audio",
        config=LIVE_CONFIG,
    )
```

---

## 2. Real-time Audio Streaming — Send and Receive

```python
import asyncio
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
client = genai.Client()


async def voice_session(audio_input_queue: asyncio.Queue, audio_output_queue: asyncio.Queue) -> None:
    """
    Bidirectional audio streaming session.

    Args:
        audio_input_queue: Queue of raw PCM bytes from the user microphone.
        audio_output_queue: Queue where synthesized PCM bytes are placed for playback.
    """
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
    )

    try:
        async with client.aio.live.connect(
            model="gemini-live-2.5-flash-native-audio",
            config=config,
        ) as session:
            send_task = asyncio.create_task(_send_audio(session, audio_input_queue))
            receive_task = asyncio.create_task(_receive_audio(session, audio_output_queue))
            await asyncio.gather(send_task, receive_task)

    except Exception as exc:
        logger.error(
            "Live API session failed",
            exc_info=exc,
            extra={"model": "gemini-live-2.5-flash-native-audio"},
        )
        raise


async def _send_audio(session, audio_input_queue: asyncio.Queue) -> None:
    """Send raw PCM chunks to the Live API session."""
    try:
        while True:
            chunk: bytes = await audio_input_queue.get()
            if chunk is None:
                # None is the sentinel to end the session
                await session.send(input=types.AudioChunk(data=b""), end_of_turn=True)
                break
            await session.send(
                input=types.AudioChunk(
                    data=chunk,
                    mime_type="audio/pcm;rate=16000",
                )
            )
    except Exception as exc:
        logger.error("Audio send failed", exc_info=exc)
        raise


async def _receive_audio(session, audio_output_queue: asyncio.Queue) -> None:
    """Receive synthesized audio bytes from the Live API session."""
    try:
        async for response in session.receive():
            if response.data:
                await audio_output_queue.put(response.data)
            if response.server_content and response.server_content.turn_complete:
                logger.info("Model turn complete")
                await audio_output_queue.put(None)  # signal end of response
    except Exception as exc:
        logger.error("Audio receive failed", exc_info=exc)
        raise
```

---

## 3. Barge-in Handling (Interrupt Detection)

The Live API natively supports barge-in — when the user starts speaking while the model is outputting audio, the model stops. Your client must:
1. Detect that the model was interrupted (`interrupted=True` in server content)
2. Discard buffered audio that was not played
3. Resume listening immediately

```python
async def _receive_audio_with_barge_in(session, audio_output_queue: asyncio.Queue) -> None:
    """Receive audio and handle barge-in interruption."""
    pending_chunks: list[bytes] = []

    try:
        async for response in session.receive():
            if response.server_content:
                sc = response.server_content

                if sc.interrupted:
                    # Model was interrupted — discard unplayed audio
                    logger.info("Barge-in detected — discarding %d buffered chunks", len(pending_chunks))
                    pending_chunks.clear()
                    # Signal downstream to stop playback
                    await audio_output_queue.put({"type": "interrupt"})
                    continue

                if response.data:
                    pending_chunks.append(response.data)
                    await audio_output_queue.put({"type": "audio", "data": response.data})

                if sc.turn_complete:
                    logger.info("Turn complete — %d chunks delivered", len(pending_chunks))
                    pending_chunks.clear()
                    await audio_output_queue.put({"type": "turn_complete"})

    except Exception as exc:
        logger.error("Barge-in receive loop failed", exc_info=exc)
        raise
```

---

## 4. Multimodal Input — Audio + Camera

```python
import base64
import asyncio
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
client = genai.Client()


async def multimodal_session(
    audio_queue: asyncio.Queue,
    video_frame_queue: asyncio.Queue,
    output_queue: asyncio.Queue,
) -> None:
    """
    Send audio + video frames simultaneously to Live API.

    Video frames must be JPEG bytes captured from camera at ~1fps.
    Audio must be PCM 16-bit 16kHz mono.
    """
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Lyra")
            )
        ),
    )

    try:
        async with client.aio.live.connect(
            model="gemini-live-2.5-flash-native-audio",
            config=config,
        ) as session:
            await asyncio.gather(
                _send_audio_stream(session, audio_queue),
                _send_video_frames(session, video_frame_queue),
                _receive_audio(session, output_queue),
            )
    except Exception as exc:
        logger.error("Multimodal session failed", exc_info=exc)
        raise


async def _send_video_frames(session, video_frame_queue: asyncio.Queue) -> None:
    """Send JPEG frames from camera to Live API."""
    try:
        while True:
            frame_bytes: bytes | None = await video_frame_queue.get()
            if frame_bytes is None:
                break
            await session.send(
                input=types.Blob(
                    data=frame_bytes,
                    mime_type="image/jpeg",
                )
            )
    except Exception as exc:
        logger.error("Video frame send failed", exc_info=exc)
        raise


async def _send_audio_stream(session, audio_queue: asyncio.Queue) -> None:
    """Send PCM audio chunks to Live API."""
    try:
        while True:
            chunk: bytes | None = await audio_queue.get()
            if chunk is None:
                break
            await session.send(
                input=types.AudioChunk(data=chunk, mime_type="audio/pcm;rate=16000")
            )
    except Exception as exc:
        logger.error("Audio stream send failed", exc_info=exc)
        raise
```

---

## 5. FastAPI WebSocket Endpoint — Browser-to-Gemini Proxy

```python
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
client = genai.Client()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Voice API server starting")
    yield
    logger.info("Voice API server shutting down")


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket proxy: browser audio bytes <-> Gemini Live API.

    Client sends: raw PCM bytes (16-bit, 16kHz, mono)
    Client receives: raw PCM bytes for playback
    Special message: b"END" signals end of user turn
    """
    await websocket.accept()
    logger.info("WebSocket voice connection opened")

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
    )

    try:
        async with client.aio.live.connect(
            model="gemini-live-2.5-flash-native-audio",
            config=config,
        ) as session:
            receive_task = asyncio.create_task(
                _relay_gemini_to_client(session, websocket)
            )

            # Forward browser audio to Gemini
            while True:
                try:
                    data = await websocket.receive_bytes()
                except WebSocketDisconnect:
                    logger.info("WebSocket client disconnected")
                    break

                if data == b"END":
                    await session.send(end_of_turn=True)
                    logger.info("End of user turn signaled to Gemini")
                else:
                    await session.send(
                        input=types.AudioChunk(data=data, mime_type="audio/pcm;rate=16000")
                    )

            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during session setup")
    except Exception as exc:
        logger.error("Voice WebSocket session error", exc_info=exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
        raise


async def _relay_gemini_to_client(session, websocket: WebSocket) -> None:
    """Forward synthesized audio from Gemini back to the browser client."""
    try:
        async for response in session.receive():
            if response.data:
                await websocket.send_bytes(response.data)
            if response.server_content and response.server_content.turn_complete:
                # Send a sentinel so client knows response is done
                await websocket.send_text("TURN_COMPLETE")
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        logger.info("Client disconnected during relay")
    except Exception as exc:
        logger.error("Gemini-to-client relay failed", exc_info=exc)
        raise
```

---

## 6. LangGraph StateGraph Node — Voice I/O

```python
import asyncio
import logging
from typing import TypedDict

from langgraph.graph import StateGraph, END
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
client = genai.Client()


class VoiceState(TypedDict):
    audio_input: bytes          # raw PCM from user
    transcript: str             # transcribed text (from Live API)
    response_text: str          # LLM-generated response
    audio_output: bytes         # synthesized audio bytes
    error: str | None


async def voice_input_node(state: VoiceState) -> VoiceState:
    """
    LangGraph node: stream user audio through Live API to get transcript.
    Live API performs transcription as part of real-time processing.
    """
    audio_input = state.get("audio_input", b"")
    if not audio_input:
        logger.error("voice_input_node received empty audio_input")
        raise ValueError("audio_input is required and must not be empty")

    transcript_parts: list[str] = []

    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],  # Text mode for transcription node
        system_instruction=types.Content(
            parts=[types.Part(text="Transcribe the user's speech exactly. Output only the transcript.")]
        ),
    )

    try:
        async with client.aio.live.connect(
            model="gemini-live-2.5-flash-native-audio",
            config=config,
        ) as session:
            await session.send(
                input=types.AudioChunk(data=audio_input, mime_type="audio/pcm;rate=16000"),
            )
            await session.send(end_of_turn=True)

            async for response in session.receive():
                if response.text:
                    transcript_parts.append(response.text)
                if response.server_content and response.server_content.turn_complete:
                    break

        transcript = "".join(transcript_parts).strip()
        logger.info("Transcribed audio", extra={"transcript_length": len(transcript)})
        return {**state, "transcript": transcript, "error": None}

    except Exception as exc:
        logger.error("voice_input_node failed", exc_info=exc)
        raise


async def voice_output_node(state: VoiceState) -> VoiceState:
    """
    LangGraph node: synthesize response_text to audio via Live API.
    """
    response_text = state.get("response_text", "")
    if not response_text:
        logger.error("voice_output_node received empty response_text")
        raise ValueError("response_text is required and must not be empty")

    audio_chunks: list[bytes] = []

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
    )

    try:
        async with client.aio.live.connect(
            model="gemini-live-2.5-flash-native-audio",
            config=config,
        ) as session:
            await session.send(input=response_text, end_of_turn=True)

            async for response in session.receive():
                if response.data:
                    audio_chunks.append(response.data)
                if response.server_content and response.server_content.turn_complete:
                    break

        audio_output = b"".join(audio_chunks)
        logger.info("Voice output synthesized", extra={"audio_bytes": len(audio_output)})
        return {**state, "audio_output": audio_output, "error": None}

    except Exception as exc:
        logger.error("voice_output_node failed", exc_info=exc)
        raise


def build_voice_graph() -> StateGraph:
    """Assemble a minimal voice I/O StateGraph (transcription + synthesis nodes)."""
    graph = StateGraph(VoiceState)
    graph.add_node("voice_input", voice_input_node)
    graph.add_node("voice_output", voice_output_node)
    graph.set_entry_point("voice_input")
    graph.add_edge("voice_input", "voice_output")
    graph.add_edge("voice_output", END)
    return graph.compile()
```

---

## 7. Error Handling Reference

| Error | Cause | Handling |
|-------|-------|----------|
| `asyncio.CancelledError` | Session cancelled (barge-in, shutdown) | Let propagate — do NOT suppress |
| `websockets.ConnectionClosed` | Network drop | Log + raise; let caller decide retry |
| `google.api_core.exceptions.ResourceExhausted` | Rate limit (429) | Exponential backoff, max 3 retries |
| `google.api_core.exceptions.Unauthenticated` | Bad API key | Log "API key invalid", raise immediately |
| Audio format mismatch | Non-PCM or wrong rate sent | Validate before send: 16-bit, 16kHz, mono |
| Empty audio input | Silent microphone or buffer issue | Raise `ValueError` — never send empty bytes |

```python
from google.api_core import exceptions as google_exceptions
import asyncio
import logging

logger = logging.getLogger(__name__)


async def with_rate_limit_retry(coro, max_retries: int = 3):
    """Retry a coroutine on rate limit with exponential backoff."""
    delay = 1.0
    for attempt in range(max_retries):
        try:
            return await coro
        except google_exceptions.ResourceExhausted as exc:
            if attempt == max_retries - 1:
                logger.error("Rate limit exceeded after %d retries", max_retries, exc_info=exc)
                raise
            logger.warning("Rate limited — retrying in %.1fs (attempt %d)", delay, attempt + 1)
            await asyncio.sleep(delay)
            delay *= 2
        except google_exceptions.Unauthenticated as exc:
            logger.error("Gemini API authentication failed — check GOOGLE_API_KEY", exc_info=exc)
            raise  # No retry for auth failures
```

---

## 8. Voice Selection Guide

| Voice | Characteristics | Best For |
|-------|----------------|----------|
| Aoede | Warm, conversational | General assistant, customer support |
| Lyra | Clear, neutral | Information delivery, e-learning |
| Orion | Confident, energetic | Interactive characters, gaming |

Style can be influenced via system instruction:
```python
system_instruction="Speak in a calm, empathetic tone suitable for mental wellness conversations."
```
