# Gemini TTS — Text-to-Speech Models

> Models: `gemini-2.5-pro-tts-preview` (high fidelity), `gemini-2.5-flash-tts-preview` (fast/cheap)
> SDK: `google-genai` (Python) — NEVER `google-generativeai` (deprecated)

## Overview

Gemini TTS converts text to high-quality speech with natural language style control. Features:
- **Style via natural language**: "whispered mysterious tone", "enthusiastic Australian accent"
- **Multi-speaker**: named speakers for podcast/dialogue generation
- **70+ languages**: mid-sentence language switching supported
- **Output**: raw PCM bytes (convertible to WAV/MP3)

---

## 1. Model Selection Guide

| Scenario | Model | Reason |
|----------|-------|--------|
| Production audiobook | `gemini-2.5-pro-tts-preview` | Highest naturalness, prosody fidelity |
| Podcast / interview dialogue | `gemini-2.5-pro-tts-preview` | Multi-speaker quality critical |
| Real-time assistant reply | `gemini-2.5-flash-tts-preview` | Lower latency, cost-efficient |
| E-learning narration | `gemini-2.5-flash-tts-preview` | Good quality at scale |
| Video voiceover (draft) | `gemini-2.5-flash-tts-preview` | Fast iteration |
| Video voiceover (final) | `gemini-2.5-pro-tts-preview` | Production quality |
| Notification / short text | `gemini-2.5-flash-tts-preview` | Overkill to use pro for short phrases |

---

## 2. Single-Speaker TTS with Style Control

```python
import logging
import wave
import io
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
client = genai.Client()


def synthesize_speech(
    text: str,
    *,
    style_prompt: str = "",
    model: str = "gemini-2.5-flash-tts-preview",
    voice_name: str = "Aoede",
) -> bytes:
    """
    Synthesize speech from text.

    Args:
        text: The text to synthesize.
        style_prompt: Natural language style instruction.
                      Examples:
                        "Speak in a warm, friendly tone"
                        "whispered mysterious tone"
                        "enthusiastic Australian accent"
                        "slow and deliberate, as if explaining to a child"
        model: TTS model ID.
        voice_name: Preset voice (Aoede, Lyra, Orion).

    Returns:
        Raw PCM audio bytes (16-bit, 24kHz, mono).

    Raises:
        ValueError: If text is empty.
        google.api_core.exceptions.GoogleAPIError: On API failure.
    """
    if not text or not text.strip():
        logger.error("synthesize_speech called with empty text")
        raise ValueError("text must not be empty")

    # Combine style instruction with content
    contents = f"{style_prompt}\n\n{text}".strip() if style_prompt else text

    logger.info(
        "Synthesizing speech",
        extra={"model": model, "voice": voice_name, "text_length": len(text)},
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                ),
            ),
        )
    except Exception as exc:
        logger.error("TTS synthesis failed", exc_info=exc, extra={"model": model})
        raise

    audio_data = response.candidates[0].content.parts[0].inline_data.data
    if not audio_data:
        logger.error("TTS returned empty audio data", extra={"model": model})
        raise RuntimeError("TTS API returned empty audio — content may have been blocked")

    logger.info("Speech synthesis complete", extra={"audio_bytes": len(audio_data)})
    return audio_data
```

---

## 3. Multi-Speaker TTS — Podcast / Dialogue

```python
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
client = genai.Client()


def synthesize_dialogue(
    turns: list[dict[str, str]],
    model: str = "gemini-2.5-pro-tts-preview",
) -> bytes:
    """
    Synthesize a multi-speaker dialogue.

    Args:
        turns: List of {"speaker": "Host", "text": "Welcome to the show!"}.
               Each unique speaker name gets a consistent voice.
               Maximum 2 named speakers per request.
        model: TTS model (pro recommended for podcasts).

    Returns:
        Raw PCM bytes of the complete dialogue.

    Raises:
        ValueError: If turns is empty or speaker count exceeds 2.
    """
    if not turns:
        logger.error("synthesize_dialogue called with empty turns")
        raise ValueError("turns must not be empty")

    unique_speakers = list({t["speaker"] for t in turns})
    if len(unique_speakers) > 2:
        logger.error(
            "Too many speakers for multi-speaker TTS",
            extra={"speaker_count": len(unique_speakers)},
        )
        raise ValueError(f"Maximum 2 speakers supported, got {len(unique_speakers)}")

    # Build the script text with speaker labels
    script = "\n\n".join(
        f'{turn["speaker"]}: {turn["text"]}' for turn in turns
    )

    # Assign voices: first speaker gets Aoede, second gets Orion
    voice_assignments = {
        unique_speakers[0]: "Aoede",
        unique_speakers[1]: "Orion" if len(unique_speakers) > 1 else "Aoede",
    }
    multi_speaker_config = types.MultiSpeakerVoiceConfig(
        speaker_voice_configs=[
            types.SpeakerVoiceConfig(
                speaker=speaker,
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                ),
            )
            for speaker, voice in voice_assignments.items()
        ]
    )

    logger.info(
        "Synthesizing dialogue",
        extra={"turns": len(turns), "speakers": unique_speakers, "model": model},
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=script,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=multi_speaker_config
                ),
            ),
        )
    except Exception as exc:
        logger.error("Multi-speaker TTS failed", exc_info=exc)
        raise

    audio_data = response.candidates[0].content.parts[0].inline_data.data
    if not audio_data:
        logger.error("Multi-speaker TTS returned empty audio")
        raise RuntimeError("Multi-speaker TTS returned empty audio — content may have been blocked")

    logger.info("Dialogue synthesis complete", extra={"audio_bytes": len(audio_data)})
    return audio_data
```

---

## 4. Language Switching Mid-Sentence

```python
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
client = genai.Client()


def synthesize_multilingual(
    text: str,
    model: str = "gemini-2.5-flash-tts-preview",
    voice_name: str = "Lyra",
) -> bytes:
    """
    Synthesize text that switches languages mid-sentence.

    Gemini TTS auto-detects language switches — no explicit markup needed.
    Supports 70+ languages. Simply write the text naturally.

    Example text:
        "Welcome to our service. Bienvenido a nuestro servicio.
         我们很高兴为您服务。Nous sommes heureux de vous servir."
    """
    if not text or not text.strip():
        raise ValueError("text must not be empty")

    logger.info(
        "Synthesizing multilingual speech",
        extra={"model": model, "text_length": len(text)},
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                ),
            ),
        )
    except Exception as exc:
        logger.error("Multilingual TTS failed", exc_info=exc)
        raise

    audio_data = response.candidates[0].content.parts[0].inline_data.data
    if not audio_data:
        raise RuntimeError("Multilingual TTS returned empty audio")

    return audio_data
```

---

## 5. Save Audio to File (WAV / MP3)

```python
import wave
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# PCM specs from Gemini TTS
SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit


def save_as_wav(audio_bytes: bytes, output_path: str | Path) -> Path:
    """
    Save raw PCM audio bytes from Gemini TTS as a WAV file.

    Args:
        audio_bytes: Raw PCM bytes from synthesize_speech().
        output_path: Destination file path (.wav extension recommended).

    Returns:
        Path to the saved file.
    """
    output_path = Path(output_path)
    if not audio_bytes:
        logger.error("save_as_wav called with empty audio bytes")
        raise ValueError("audio_bytes must not be empty")

    try:
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(audio_bytes)
    except Exception as exc:
        logger.error("Failed to save WAV file", exc_info=exc, extra={"path": str(output_path)})
        raise

    logger.info("WAV file saved", extra={"path": str(output_path), "bytes": len(audio_bytes)})
    return output_path


def save_as_mp3(audio_bytes: bytes, output_path: str | Path) -> Path:
    """
    Convert and save raw PCM bytes as MP3 using pydub.

    Requires: uv add pydub && brew install ffmpeg (macOS) or apt install ffmpeg (Linux)
    """
    try:
        from pydub import AudioSegment
    except ImportError as exc:
        logger.error("pydub not installed — run: uv add pydub", exc_info=exc)
        raise ImportError("pydub required for MP3 export. Run: uv add pydub") from exc

    output_path = Path(output_path)

    try:
        audio_segment = AudioSegment(
            data=audio_bytes,
            sample_width=SAMPLE_WIDTH,
            frame_rate=SAMPLE_RATE,
            channels=CHANNELS,
        )
        audio_segment.export(str(output_path), format="mp3")
    except Exception as exc:
        logger.error("Failed to save MP3 file", exc_info=exc, extra={"path": str(output_path)})
        raise

    logger.info("MP3 file saved", extra={"path": str(output_path)})
    return output_path
```

---

## 6. FastAPI Endpoint — TTS API

```python
import logging
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)


class TTSRequest(BaseModel):
    text: str
    model: str = "gemini-2.5-flash-tts-preview"
    voice: str = "Aoede"
    style: str = ""

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must not be empty")
        return v

    @field_validator("model")
    @classmethod
    def valid_model(cls, v: str) -> str:
        allowed = {"gemini-2.5-pro-tts-preview", "gemini-2.5-flash-tts-preview"}
        if v not in allowed:
            raise ValueError(f"model must be one of {allowed}")
        return v

    @field_validator("voice")
    @classmethod
    def valid_voice(cls, v: str) -> str:
        allowed = {"Aoede", "Lyra", "Orion"}
        if v not in allowed:
            raise ValueError(f"voice must be one of {allowed}")
        return v


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TTS API server starting")
    yield
    logger.info("TTS API server shutting down")


app = FastAPI(lifespan=lifespan)


@app.post("/tts", response_class=StreamingResponse)
async def text_to_speech(request: TTSRequest) -> StreamingResponse:
    """
    Synthesize speech from text.

    Returns WAV audio bytes as a streaming response.
    """
    import asyncio
    from .synthesize import synthesize_speech  # import your synthesis function

    try:
        # Run blocking synthesis in thread pool to avoid blocking event loop
        audio_bytes = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: synthesize_speech(
                request.text,
                style_prompt=request.style,
                model=request.model,
                voice_name=request.voice,
            ),
        )
    except ValueError as exc:
        logger.warning("TTS validation error", extra={"error": str(exc)})
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        logger.error("TTS synthesis error", exc_info=exc)
        raise HTTPException(status_code=502, detail="Speech synthesis failed")
    except Exception as exc:
        logger.error("Unexpected TTS error", exc_info=exc)
        raise HTTPException(status_code=500, detail="Internal server error")

    return StreamingResponse(
        BytesIO(audio_bytes),
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=speech.wav"},
    )
```

---

## 7. Streaming TTS for Lower Latency

For long texts, stream chunks as they arrive rather than waiting for full synthesis:

```python
import logging
from google import genai
from google.genai import types
from typing import AsyncIterator

logger = logging.getLogger(__name__)
client = genai.Client()


async def stream_tts(
    text: str,
    model: str = "gemini-2.5-flash-tts-preview",
    voice_name: str = "Aoede",
) -> AsyncIterator[bytes]:
    """
    Stream TTS audio chunks as they arrive for lower time-to-first-audio.

    Yields raw PCM byte chunks. Caller must assemble or play directly.
    """
    if not text or not text.strip():
        logger.error("stream_tts called with empty text")
        raise ValueError("text must not be empty")

    logger.info("Starting streaming TTS", extra={"model": model, "text_length": len(text)})

    try:
        async for chunk in await client.aio.models.generate_content_stream(
            model=model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                ),
            ),
        ):
            if chunk.candidates and chunk.candidates[0].content.parts:
                part = chunk.candidates[0].content.parts[0]
                if hasattr(part, "inline_data") and part.inline_data.data:
                    yield part.inline_data.data

    except Exception as exc:
        logger.error("Streaming TTS failed", exc_info=exc, extra={"model": model})
        raise
```

---

## 8. Error Handling Reference

| Error | Cause | Handling |
|-------|-------|----------|
| `ValueError: text must not be empty` | Empty input | Validate before calling API |
| `google.api_core.exceptions.ResourceExhausted` | Rate limit (429) | Exponential backoff, max 3 retries |
| `google.api_core.exceptions.InvalidArgument` | Unsupported language or malformed request | Log + raise HTTPException 422 |
| `google.api_core.exceptions.PermissionDenied` | Content policy block | Log blocked category (never log content), raise 422 |
| `RuntimeError: empty audio` | API returned no audio bytes | Content likely blocked — surface to user |
| `ImportError: pydub` | MP3 export without pydub installed | Install pydub + ffmpeg, or export as WAV |

```python
from google.api_core import exceptions as google_exceptions
import asyncio
import logging

logger = logging.getLogger(__name__)


async def synthesize_with_retry(text: str, **kwargs) -> bytes:
    """Synthesize speech with exponential backoff retry on rate limits."""
    from .synthesize import synthesize_speech
    import asyncio

    delay = 1.0
    max_retries = 3

    for attempt in range(max_retries):
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: synthesize_speech(text, **kwargs)
            )
        except google_exceptions.ResourceExhausted as exc:
            if attempt == max_retries - 1:
                logger.error("TTS rate limit exceeded after %d retries", max_retries, exc_info=exc)
                raise
            logger.warning("TTS rate limited — retrying in %.1fs", delay)
            await asyncio.sleep(delay)
            delay *= 2
        except google_exceptions.PermissionDenied as exc:
            logger.error("TTS content policy block — content not synthesized", exc_info=exc)
            raise RuntimeError("Content blocked by policy") from exc
        except google_exceptions.Unauthenticated as exc:
            logger.error("TTS auth failed — check GOOGLE_API_KEY", exc_info=exc)
            raise
```
