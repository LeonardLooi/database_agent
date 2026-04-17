# LangGraph + Gemini Voice Agent

> Framework: LangGraph v1.0.7 + LangChain v1.2.8 + FastAPI 0.135.2
> Models: `gemini-live-2.5-flash-native-audio` (Live), `gemini-2.5-flash-tts-preview` (TTS)
> Python: 3.14 + asyncio

## Architecture

```
User audio (PCM) --> [voice_input_node] --> transcript
                                               |
                                    [llm_response_node]
                                               |
                                         response_text
                                               |
                                    [voice_output_node] --> audio bytes
```

State flows through a LangGraph `StateGraph`. Each node is independently testable.

---

## 1. State Definition

```python
from typing import TypedDict


class VoiceAgentState(TypedDict):
    """
    Shared state across all nodes in the voice agent graph.

    audio_input:   Raw PCM bytes from user microphone (16-bit, 16kHz, mono).
    transcript:    Text transcription of the user's speech.
    response_text: LLM-generated text response.
    audio_output:  Synthesized audio bytes (PCM) for playback.
    error:         Error message if any node failed; None on success.
    session_id:    Identifier for the conversation session (for logging/tracing).
    turn_count:    Number of conversation turns completed.
    """
    audio_input: bytes
    transcript: str
    response_text: str
    audio_output: bytes
    error: str | None
    session_id: str
    turn_count: int
```

---

## 2. Voice Input Node — Transcription via Live API

```python
import asyncio
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
client = genai.Client()


async def voice_input_node(state: VoiceAgentState) -> VoiceAgentState:
    """
    Transcribe user audio using Gemini Live API in TEXT response mode.

    The Live API performs speech recognition as part of its processing.
    TEXT response mode returns the transcript rather than synthesized audio.
    """
    audio_input = state.get("audio_input", b"")
    session_id = state.get("session_id", "unknown")

    if not audio_input:
        logger.error(
            "voice_input_node: audio_input is empty",
            extra={"session_id": session_id},
        )
        raise ValueError("audio_input must not be empty")

    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction=types.Content(
            parts=[types.Part(
                text="Transcribe the user's audio input exactly as spoken. "
                     "Output only the transcript — no commentary, no corrections."
            )]
        ),
    )

    transcript_parts: list[str] = []

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

    except Exception as exc:
        logger.error(
            "voice_input_node: Live API transcription failed",
            exc_info=exc,
            extra={"session_id": session_id},
        )
        raise

    transcript = "".join(transcript_parts).strip()
    if not transcript:
        logger.warning(
            "voice_input_node: empty transcript received",
            extra={"session_id": session_id, "audio_bytes": len(audio_input)},
        )

    logger.info(
        "voice_input_node: transcription complete",
        extra={"session_id": session_id, "transcript_length": len(transcript)},
    )

    return {
        **state,
        "transcript": transcript,
        "error": None,
    }
```

---

## 3. LLM Response Node — Agent Logic

```python
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


def build_llm(model: str = "gemini-2.5-flash") -> ChatGoogleGenerativeAI:
    """Build LangChain LLM wrapper for Gemini."""
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=0.7,
        max_output_tokens=512,
    )


_llm = build_llm()

SYSTEM_PROMPT = (
    "You are a helpful voice assistant. "
    "Respond concisely — your answer will be spoken aloud. "
    "Avoid lists, markdown, or formatting. Plain natural speech only."
)


async def llm_response_node(state: VoiceAgentState) -> VoiceAgentState:
    """
    Generate a text response from the transcript using LangChain + Gemini.
    """
    transcript = state.get("transcript", "")
    session_id = state.get("session_id", "unknown")

    if not transcript:
        logger.warning(
            "llm_response_node: empty transcript — using fallback response",
            extra={"session_id": session_id},
        )
        return {
            **state,
            "response_text": "I didn't catch that. Could you please repeat?",
            "error": None,
        }

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=transcript),
    ]

    logger.info(
        "llm_response_node: generating response",
        extra={"session_id": session_id, "transcript_length": len(transcript)},
    )

    try:
        response = await _llm.ainvoke(messages)
        response_text = response.content.strip()
    except Exception as exc:
        logger.error(
            "llm_response_node: LLM invocation failed",
            exc_info=exc,
            extra={"session_id": session_id},
        )
        raise

    logger.info(
        "llm_response_node: response generated",
        extra={"session_id": session_id, "response_length": len(response_text)},
    )

    return {
        **state,
        "response_text": response_text,
        "turn_count": state.get("turn_count", 0) + 1,
        "error": None,
    }
```

---

## 4. Voice Output Node — TTS Synthesis

```python
import asyncio
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
client = genai.Client()


async def voice_output_node(state: VoiceAgentState) -> VoiceAgentState:
    """
    Synthesize response_text to audio using Gemini TTS.

    Uses gemini-2.5-flash-tts-preview for real-time response speed.
    Switch to gemini-2.5-pro-tts-preview for higher fidelity requirements.
    """
    response_text = state.get("response_text", "")
    session_id = state.get("session_id", "unknown")

    if not response_text:
        logger.error(
            "voice_output_node: response_text is empty",
            extra={"session_id": session_id},
        )
        raise ValueError("response_text must not be empty before voice synthesis")

    logger.info(
        "voice_output_node: synthesizing audio",
        extra={"session_id": session_id, "text_length": len(response_text)},
    )

    audio_chunks: list[bytes] = []

    try:
        # Run blocking TTS in executor to avoid blocking the event loop
        def _synthesize() -> bytes:
            _client = genai.Client()
            response = _client.models.generate_content(
                model="gemini-2.5-flash-tts-preview",
                contents=response_text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Aoede"
                            )
                        )
                    ),
                ),
            )
            data = response.candidates[0].content.parts[0].inline_data.data
            if not data:
                raise RuntimeError("TTS returned empty audio — content may be blocked")
            return data

        audio_bytes = await asyncio.get_event_loop().run_in_executor(None, _synthesize)

    except Exception as exc:
        logger.error(
            "voice_output_node: TTS synthesis failed",
            exc_info=exc,
            extra={"session_id": session_id},
        )
        raise

    logger.info(
        "voice_output_node: synthesis complete",
        extra={"session_id": session_id, "audio_bytes": len(audio_bytes)},
    )

    return {
        **state,
        "audio_output": audio_bytes,
        "error": None,
    }
```

---

## 5. Graph Assembly

```python
import logging
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


def build_voice_agent_graph():
    """
    Assemble the voice agent StateGraph.

    Flow: voice_input -> llm_response -> voice_output -> END
    """
    graph = StateGraph(VoiceAgentState)

    graph.add_node("voice_input", voice_input_node)
    graph.add_node("llm_response", llm_response_node)
    graph.add_node("voice_output", voice_output_node)

    graph.set_entry_point("voice_input")
    graph.add_edge("voice_input", "llm_response")
    graph.add_edge("llm_response", "voice_output")
    graph.add_edge("voice_output", END)

    compiled = graph.compile()
    logger.info("Voice agent graph compiled: voice_input -> llm_response -> voice_output -> END")
    return compiled


# Module-level compiled graph — one instance per service
voice_agent = build_voice_agent_graph()
```

---

## 6. FastAPI Streaming Endpoint — End-to-End

```python
import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Voice agent API starting — graph compiled")
    yield
    logger.info("Voice agent API shutting down")


app = FastAPI(lifespan=lifespan)


class VoiceTurnRequest(BaseModel):
    """For HTTP turn-based voice (non-streaming)."""
    audio_base64: str  # Base64-encoded PCM bytes
    session_id: str = ""


@app.post("/voice/turn")
async def voice_turn(request: VoiceTurnRequest) -> dict:
    """
    Single-turn voice interaction: audio in -> audio out.

    Accepts base64-encoded PCM bytes, returns base64-encoded PCM response.
    For real-time streaming, use the WebSocket endpoint instead.
    """
    import base64

    session_id = request.session_id or str(uuid.uuid4())

    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception as exc:
        logger.warning("Invalid base64 audio input", exc_info=exc, extra={"session_id": session_id})
        raise HTTPException(status_code=422, detail="audio_base64 must be valid base64-encoded PCM bytes")

    if not audio_bytes:
        raise HTTPException(status_code=422, detail="audio_base64 decoded to empty bytes")

    initial_state: VoiceAgentState = {
        "audio_input": audio_bytes,
        "transcript": "",
        "response_text": "",
        "audio_output": b"",
        "error": None,
        "session_id": session_id,
        "turn_count": 0,
    }

    try:
        result = await voice_agent.ainvoke(initial_state)
    except Exception as exc:
        logger.error("Voice agent turn failed", exc_info=exc, extra={"session_id": session_id})
        raise HTTPException(status_code=502, detail="Voice agent processing failed")

    if result.get("error"):
        logger.error(
            "Voice agent returned error state",
            extra={"session_id": session_id, "error": result["error"]},
        )
        raise HTTPException(status_code=502, detail=result["error"])

    return {
        "session_id": session_id,
        "transcript": result["transcript"],
        "response_text": result["response_text"],
        "audio_output_base64": base64.b64encode(result["audio_output"]).decode(),
        "turn_count": result["turn_count"],
    }


@app.websocket("/ws/voice/stream")
async def websocket_voice_stream(websocket: WebSocket) -> None:
    """
    WebSocket streaming voice: client sends PCM chunks, receives PCM response.

    Protocol:
      Client -> Server: raw PCM bytes (16-bit, 16kHz, mono)
      Client -> Server: b"END" to signal end of turn
      Server -> Client: raw PCM bytes (response audio)
      Server -> Client: text "TURN_COMPLETE" when done
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info("WebSocket voice stream opened", extra={"session_id": session_id})

    audio_chunks: list[bytes] = []

    try:
        while True:
            try:
                data = await websocket.receive_bytes()
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected", extra={"session_id": session_id})
                break

            if data == b"END":
                if not audio_chunks:
                    await websocket.send_text("ERROR:empty_audio")
                    continue

                combined_audio = b"".join(audio_chunks)
                audio_chunks.clear()

                initial_state: VoiceAgentState = {
                    "audio_input": combined_audio,
                    "transcript": "",
                    "response_text": "",
                    "audio_output": b"",
                    "error": None,
                    "session_id": session_id,
                    "turn_count": 0,
                }

                try:
                    result = await voice_agent.ainvoke(initial_state)
                except Exception as exc:
                    logger.error(
                        "Voice agent processing failed",
                        exc_info=exc,
                        extra={"session_id": session_id},
                    )
                    await websocket.send_text("ERROR:processing_failed")
                    continue

                if result.get("audio_output"):
                    await websocket.send_bytes(result["audio_output"])
                await websocket.send_text("TURN_COMPLETE")

            else:
                audio_chunks.append(data)

    except Exception as exc:
        logger.error(
            "WebSocket voice stream error",
            exc_info=exc,
            extra={"session_id": session_id},
        )
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
        raise
```

---

## 7. End-to-End Example Flow

```
1. User presses microphone button in browser
2. Browser captures PCM audio, sends bytes via WebSocket to /ws/voice/stream
3. User releases button -> browser sends b"END"
4. voice_input_node: PCM bytes -> Gemini Live API -> transcript text
5. llm_response_node: transcript -> LangChain + Gemini -> response text
6. voice_output_node: response text -> Gemini TTS -> PCM audio bytes
7. FastAPI sends audio bytes back over WebSocket
8. Browser receives PCM, decodes, plays through Web Audio API
9. User hears the assistant's response
10. Cycle repeats for next turn
```

---

## 8. Testing the Graph

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_voice_input_node_happy_path():
    """Verify voice_input_node transcribes audio and updates state."""
    fake_pcm = b"\x00\x01" * 1000  # 2000 bytes of fake PCM

    mock_response = AsyncMock()
    mock_response.text = "Hello, how are you?"
    mock_response.server_content = AsyncMock()
    mock_response.server_content.turn_complete = True

    mock_session = AsyncMock()
    mock_session.receive = AsyncMock(return_value=aiter([mock_response]))

    with patch("google.genai.Client") as mock_client:
        mock_client.return_value.aio.live.connect.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_client.return_value.aio.live.connect.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        state: VoiceAgentState = {
            "audio_input": fake_pcm,
            "transcript": "",
            "response_text": "",
            "audio_output": b"",
            "error": None,
            "session_id": "test-session",
            "turn_count": 0,
        }

        result = await voice_input_node(state)
        assert result["transcript"] == "Hello, how are you?"
        assert result["error"] is None


async def aiter(items):
    for item in items:
        yield item
```
