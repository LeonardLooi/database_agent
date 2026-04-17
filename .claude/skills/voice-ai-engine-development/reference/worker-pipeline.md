# Worker Pipeline — BaseWorker Pattern + Gemini Implementations

Full implementation of the async worker pipeline: abstract base classes, concrete Gemini workers, and FastAPI wiring.

---

## Abstract Base Classes

### BaseWorker

```python
# src/workers/base.py
import asyncio
import structlog
from abc import ABC, abstractmethod
from typing import Any

log = structlog.get_logger()


class BaseWorker(ABC):
    """
    Every voice pipeline component inherits from BaseWorker.
    Workers communicate exclusively via asyncio.Queue — no direct method calls.
    """

    def __init__(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue) -> None:
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.active = False
        self._task: asyncio.Task | None = None
        self._log = log.bind(worker=self.__class__.__name__)

    def start(self) -> None:
        """Start the worker's processing loop as a background asyncio task."""
        self.active = True
        self._task = asyncio.create_task(self._run_loop())
        self._log.info("worker_started")

    async def _run_loop(self) -> None:
        """Main processing loop — runs until terminate() is called."""
        while self.active:
            try:
                item = await self.input_queue.get()
                await self.process(item)
            except asyncio.CancelledError:
                raise  # Never swallow CancelledError
            except Exception as exc:
                self._log.error("worker_error", error=str(exc), exc_info=True)
                # Continue loop — worker recovers from transient errors

    @abstractmethod
    async def process(self, item: Any) -> None:
        """Process one item from the input queue. Override in subclasses."""
        raise NotImplementedError

    def terminate(self) -> None:
        """Stop the worker."""
        self.active = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._log.info("worker_terminated")
```

### BaseTranscriber

```python
# src/workers/transcriber_base.py
import asyncio
from abc import abstractmethod
from .base import BaseWorker


class Transcription:
    def __init__(
        self,
        message: str,
        confidence: float = 1.0,
        is_final: bool = True,
        is_interrupt: bool = False,
    ) -> None:
        self.message = message
        self.confidence = confidence
        self.is_final = is_final
        self.is_interrupt = is_interrupt


class BaseTranscriber(BaseWorker):
    """
    Receives raw PCM audio chunks, produces Transcription objects.
    Supports mute/unmute to prevent echo during bot speech.
    """

    def __init__(self, output_queue: asyncio.Queue) -> None:
        # Transcriber's input queue receives audio bytes
        super().__init__(
            input_queue=asyncio.Queue(),
            output_queue=output_queue,
        )
        self.is_muted = False

    def send_audio(self, chunk: bytes) -> None:
        """Called by the WebSocket receiver with each incoming audio chunk."""
        if not self.is_muted:
            self.input_queue.put_nowait(chunk)
        else:
            # Send silence to keep Gemini Live session alive without echoing
            self.input_queue.put_nowait(self._silent_chunk(len(chunk)))

    def mute(self) -> None:
        """Mute transcriber when bot starts speaking — prevents echo feedback."""
        self.is_muted = True
        self._log.debug("transcriber_muted")

    def unmute(self) -> None:
        """Unmute transcriber when bot finishes speaking."""
        self.is_muted = False
        self._log.debug("transcriber_unmuted")

    @staticmethod
    def _silent_chunk(size: int) -> bytes:
        return b"\x00" * size

    @abstractmethod
    async def process(self, chunk: bytes) -> None:
        raise NotImplementedError
```

### BaseAgent

```python
# src/workers/agent_base.py
import asyncio
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator
from .base import BaseWorker
from .transcriber_base import Transcription


@dataclass
class AgentResponse:
    text: str
    is_final: bool = True
    conversation_id: str = ""


@dataclass
class ConversationHistory:
    messages: list[dict] = field(default_factory=list)

    def add_human(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_bot(self, text: str) -> None:
        self.messages.append({"role": "assistant", "content": text})

    def update_last_bot_on_cutoff(self, partial_text: str) -> None:
        """Called when bot is interrupted — update history with what was actually spoken."""
        for msg in reversed(self.messages):
            if msg["role"] == "assistant":
                msg["content"] = partial_text
                return


class BaseAgent(BaseWorker):
    """
    Receives Transcription objects, produces AgentResponse objects.
    Maintains conversation history across turns.
    """

    def __init__(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue) -> None:
        super().__init__(input_queue=input_queue, output_queue=output_queue)
        self.history = ConversationHistory()
        self._current_task: asyncio.Task | None = None

    def cancel_current_task(self) -> None:
        """Cancel in-flight generation on interrupt."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self._log.info("agent_task_cancelled")

    async def process(self, transcription: Transcription) -> None:
        self.cancel_current_task()
        self.history.add_human(transcription.message)
        self._current_task = asyncio.create_task(
            self._generate_and_enqueue(transcription)
        )

    async def _generate_and_enqueue(self, transcription: Transcription) -> None:
        try:
            full_response = ""
            async for chunk in self.generate_response(
                transcription.message,
                is_interrupt=transcription.is_interrupt,
            ):
                full_response += chunk
            # Buffer entire response before enqueuing — prevents audio jumping
            response = AgentResponse(text=full_response, conversation_id="")
            self.history.add_bot(full_response)
            await self.output_queue.put(response)
        except asyncio.CancelledError:
            self._log.info("agent_generation_cancelled")
        except Exception as exc:
            self._log.error("agent_generation_failed", error=str(exc), exc_info=True)
            raise

    @abstractmethod
    async def generate_response(
        self, human_input: str, is_interrupt: bool = False
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError
```

### BaseSynthesizer

```python
# src/workers/synthesizer_base.py
import asyncio
from abc import abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator, Callable
from .base import BaseWorker
from .agent_base import AgentResponse


@dataclass
class ChunkResult:
    chunk: bytes
    is_last_chunk: bool


@dataclass
class SynthesisResult:
    chunk_generator: AsyncGenerator[ChunkResult, None]
    get_message_up_to: Callable[[float], str]  # seconds → partial text spoken so far


class BaseSynthesizer(BaseWorker):
    """
    Receives AgentResponse objects, produces SynthesisResult for the output device.
    """

    def __init__(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue) -> None:
        super().__init__(input_queue=input_queue, output_queue=output_queue)

    async def process(self, response: AgentResponse) -> None:
        try:
            result = await self.create_speech(response)
            await self.output_queue.put(result)
        except Exception as exc:
            self._log.error("synthesizer_failed", error=str(exc), exc_info=True)
            raise

    @abstractmethod
    async def create_speech(self, response: AgentResponse) -> SynthesisResult:
        raise NotImplementedError
```

---

## Concrete Gemini Implementations

### GeminiTranscriberWorker

```python
# src/workers/gemini_transcriber.py
import asyncio
import structlog
from google import genai
from google.genai import types
from .transcriber_base import BaseTranscriber, Transcription

log = structlog.get_logger()


class GeminiTranscriberWorker(BaseTranscriber):
    """
    Streams raw PCM audio to Gemini Live API via WebSocket.
    Produces Transcription objects for the agent worker.
    Uses gemini-live-2.5-flash-native-audio with native barge-in.
    """

    def __init__(
        self,
        output_queue: asyncio.Queue,
        client: genai.Client,
        model: str = "gemini-live-2.5-flash-native-audio",
        system_instruction: str = "You are a helpful voice assistant.",
    ) -> None:
        super().__init__(output_queue=output_queue)
        self._client = client
        self._model = model
        self._system_instruction = system_instruction
        self._session: genai.live.AsyncSession | None = None
        self._receiver_task: asyncio.Task | None = None
        self._log = log.bind(worker="GeminiTranscriberWorker")

    async def connect(self) -> None:
        """Open Gemini Live API WebSocket session. Call before start()."""
        config = types.LiveConnectConfig(
            response_modalities=["TEXT"],  # TEXT for transcript; AUDIO for S2S
            system_instruction=self._system_instruction,
        )
        self._session = await self._client.aio.live.connect(
            model=self._model, config=config
        )
        self._log.info("gemini_live_connected", model=self._model)
        # Start receiver coroutine alongside sender loop
        self._receiver_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self) -> None:
        """Receive transcription responses from Gemini Live API."""
        try:
            async for response in self._session:
                if response.server_content and response.server_content.model_turn:
                    for part in response.server_content.model_turn.parts:
                        if part.text and part.text.strip():
                            transcription = Transcription(
                                message=part.text.strip(),
                                is_final=True,
                                confidence=1.0,
                            )
                            await self.output_queue.put(transcription)
                            self._log.info("transcribed", text=part.text.strip())
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._log.error("receiver_loop_failed", error=str(exc), exc_info=True)
            raise

    async def process(self, chunk: bytes) -> None:
        """Send one audio chunk to Gemini Live API."""
        if self._session is None:
            self._log.error("gemini_live_not_connected")
            raise RuntimeError("GeminiTranscriberWorker: session not connected. Call connect() first.")
        try:
            await self._session.send_realtime_input(
                types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
            )
        except Exception as exc:
            self._log.error("send_audio_failed", error=str(exc), exc_info=True)
            raise

    def terminate(self) -> None:
        super().terminate()
        if self._receiver_task and not self._receiver_task.done():
            self._receiver_task.cancel()
```

### GeminiSynthesizerWorker

```python
# src/workers/gemini_synthesizer.py
import asyncio
import structlog
from google import genai
from google.genai import types
from .synthesizer_base import BaseSynthesizer, SynthesisResult, ChunkResult
from .agent_base import AgentResponse

log = structlog.get_logger()

# Gemini TTS output: 24kHz mono 16-bit PCM
_SAMPLE_RATE = 24_000
_BYTES_PER_SAMPLE = 2
_CHUNK_SIZE = 4_096  # bytes per chunk for streaming
_SECONDS_PER_CHUNK = _CHUNK_SIZE / _BYTES_PER_SAMPLE / _SAMPLE_RATE  # ~0.085s


class GeminiSynthesizerWorker(BaseSynthesizer):
    """
    Converts agent text responses to speech using Gemini TTS.
    Streams PCM audio chunks to the output device queue.
    """

    def __init__(
        self,
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        client: genai.Client,
        model: str = "gemini-2.5-flash-tts-preview",
        voice: str = "Aoede",
    ) -> None:
        super().__init__(input_queue=input_queue, output_queue=output_queue)
        self._client = client
        self._model = model
        self._voice = voice
        self._log = log.bind(worker="GeminiSynthesizerWorker")

    async def create_speech(self, response: AgentResponse) -> SynthesisResult:
        """Synthesize text to PCM audio and return a SynthesisResult."""
        text = response.text
        self._log.info("synthesizing", chars=len(text), model=self._model, voice=self._voice)

        try:
            api_response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self._voice
                            )
                        )
                    ),
                ),
            )
        except Exception as exc:
            self._log.error("tts_api_failed", text_preview=text[:50], error=str(exc), exc_info=True)
            raise

        audio_bytes: bytes = api_response.candidates[0].content.parts[0].inline_data.data
        self._log.info("tts_synthesized", bytes=len(audio_bytes))

        # Build message-up-to function for interrupt handling
        chars_per_second = len(text) / max(len(audio_bytes) / _BYTES_PER_SAMPLE / _SAMPLE_RATE, 0.001)

        def get_message_up_to(seconds: float) -> str:
            char_count = int(seconds * chars_per_second)
            return text[:char_count]

        async def chunk_generator():
            for i in range(0, len(audio_bytes), _CHUNK_SIZE):
                chunk = audio_bytes[i : i + _CHUNK_SIZE]
                is_last = (i + _CHUNK_SIZE) >= len(audio_bytes)
                yield ChunkResult(chunk=chunk, is_last_chunk=is_last)

        return SynthesisResult(
            chunk_generator=chunk_generator(),
            get_message_up_to=get_message_up_to,
        )
```

### LangGraphAgentWorker

```python
# src/workers/langgraph_agent.py
import asyncio
import structlog
from typing import AsyncGenerator, Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from .agent_base import BaseAgent

log = structlog.get_logger()


class VoiceAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    iteration_count: int  # Iron Law: always track iterations


def build_voice_graph(llm) -> StateGraph:
    """Build a minimal LangGraph StateGraph for voice agent."""

    async def agent_node(state: VoiceAgentState):
        if state["iteration_count"] >= 10:  # Iron Law: iteration limit
            return {"messages": [AIMessage(content="I need to stop here.")], "iteration_count": state["iteration_count"] + 1}
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response], "iteration_count": state["iteration_count"] + 1}

    def should_continue(state: VoiceAgentState):
        return END  # For voice: always stop after one agent turn

    graph = StateGraph(VoiceAgentState)
    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    return graph.compile()


class LangGraphAgentWorker(BaseAgent):
    """
    Voice agent using LangGraph StateGraph.
    Maintains conversation history across turns.
    Uses ChatGoogleGenerativeAI (Gemini) as the LLM.
    """

    def __init__(
        self,
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        system_prompt: str = "You are a helpful voice assistant. Keep responses concise and conversational.",
        gemini_model: str = "gemini-2.5-flash",
        google_api_key: str | None = None,
    ) -> None:
        super().__init__(input_queue=input_queue, output_queue=output_queue)
        self._system_prompt = system_prompt
        llm = ChatGoogleGenerativeAI(
            model=gemini_model,
            google_api_key=google_api_key,
            streaming=True,
        )
        self._graph = build_voice_graph(llm)
        self._log = log.bind(worker="LangGraphAgentWorker")

    async def generate_response(
        self, human_input: str, is_interrupt: bool = False
    ) -> AsyncGenerator[str, None]:
        """Generate response via LangGraph. Yields text chunks."""
        messages = []
        if not any(m.get("role") == "system" for m in self.history.messages):
            messages.append(SystemMessage(content=self._system_prompt))
        for msg in self.history.messages:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=human_input))

        state: VoiceAgentState = {"messages": messages, "iteration_count": 0}

        try:
            result = await self._graph.ainvoke(state)
            last_message = result["messages"][-1]
            response_text = last_message.content if hasattr(last_message, "content") else str(last_message)
            self._log.info("langgraph_response_generated", chars=len(response_text))
            yield response_text
        except Exception as exc:
            self._log.error("langgraph_generation_failed", error=str(exc), exc_info=True)
            raise
```

### ADKAgentWorker

```python
# src/workers/adk_agent.py
import asyncio
import structlog
from typing import AsyncGenerator
from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types as genai_types
from .agent_base import BaseAgent

log = structlog.get_logger()


class ADKAgentWorker(BaseAgent):
    """
    Voice agent using Google ADK SequentialAgent.
    Uses ADK Runner for session-aware agent execution.
    """

    def __init__(
        self,
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        app_name: str = "voice-agent",
        system_prompt: str = "You are a helpful voice assistant. Keep responses concise.",
        gemini_model: str = "gemini-2.5-flash",
    ) -> None:
        super().__init__(input_queue=input_queue, output_queue=output_queue)
        self._app_name = app_name
        self._session_id = f"voice-session-{id(self)}"
        self._user_id = "voice-user"
        self._log = log.bind(worker="ADKAgentWorker")

        # Build ADK agent
        llm_agent = LlmAgent(
            name="voice_llm_agent",
            model=gemini_model,
            instruction=system_prompt,
        )
        self._agent = SequentialAgent(
            name="voice_sequential_agent",
            sub_agents=[llm_agent],
        )
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=self._agent,
            app_name=app_name,
            session_service=self._session_service,
        )

    async def _ensure_session(self) -> None:
        """Create ADK session if it does not exist."""
        try:
            await self._session_service.get_session(
                app_name=self._app_name,
                user_id=self._user_id,
                session_id=self._session_id,
            )
        except Exception:
            await self._session_service.create_session(
                app_name=self._app_name,
                user_id=self._user_id,
                session_id=self._session_id,
            )

    async def generate_response(
        self, human_input: str, is_interrupt: bool = False
    ) -> AsyncGenerator[str, None]:
        """Generate response via ADK SequentialAgent. Yields text chunks."""
        await self._ensure_session()

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=human_input)],
        )

        full_response = ""
        try:
            async for event in self._runner.run_async(
                user_id=self._user_id,
                session_id=self._session_id,
                new_message=content,
            ):
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if part.text:
                            full_response += part.text
            self._log.info("adk_response_generated", chars=len(full_response))
            yield full_response
        except Exception as exc:
            self._log.error("adk_generation_failed", error=str(exc), exc_info=True)
            raise
```

---

## FastAPI WebSocket Server (Pipeline Wiring)

```python
# src/main.py
import asyncio
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google import genai

from .config import VoiceEngineConfig
from .workers.gemini_transcriber import GeminiTranscriberWorker
from .workers.gemini_synthesizer import GeminiSynthesizerWorker
from .workers.langgraph_agent import LangGraphAgentWorker  # or ADKAgentWorker
from .conversation import StreamingConversation

log = structlog.get_logger()
config = VoiceEngineConfig()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.gemini_client = genai.Client(api_key=config.gemini_api_key)
    log.info("voice_engine_started")
    yield
    # Shutdown
    log.info("voice_engine_stopped")


app = FastAPI(title="Voice AI Engine", lifespan=lifespan)


@app.websocket("/conversation")
async def conversation_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    log.info("client_connected", client=websocket.client)

    # Build queues
    transcription_queue: asyncio.Queue = asyncio.Queue()
    agent_queue: asyncio.Queue = asyncio.Queue()
    synthesis_queue: asyncio.Queue = asyncio.Queue()

    client: genai.Client = websocket.app.state.gemini_client

    # Instantiate workers
    transcriber = GeminiTranscriberWorker(
        output_queue=transcription_queue,
        client=client,
        model=config.gemini_live_model,
        system_instruction="You are a helpful voice assistant.",
    )
    agent = LangGraphAgentWorker(
        input_queue=transcription_queue,
        output_queue=agent_queue,
        google_api_key=config.gemini_api_key,
    )
    synthesizer = GeminiSynthesizerWorker(
        input_queue=agent_queue,
        output_queue=synthesis_queue,
        client=client,
        model=config.gemini_tts_model,
        voice=config.gemini_tts_voice,
    )

    # Create conversation orchestrator
    conversation = StreamingConversation(
        websocket=websocket,
        transcriber=transcriber,
        agent=agent,
        synthesizer=synthesizer,
        synthesis_queue=synthesis_queue,
    )

    try:
        await conversation.start()

        async for message in websocket.iter_bytes():
            conversation.receive_audio(message)

    except WebSocketDisconnect:
        log.info("client_disconnected")
    except Exception as exc:
        log.error("conversation_error", error=str(exc), exc_info=True)
        raise
    finally:
        await conversation.terminate()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

---

## StreamingConversation Orchestrator

```python
# src/conversation.py
import asyncio
import time
import structlog
from fastapi import WebSocket

from .workers.transcriber_base import BaseTranscriber
from .workers.agent_base import BaseAgent
from .workers.synthesizer_base import BaseSynthesizer, SynthesisResult

log = structlog.get_logger()

# Audio chunk timing: 24kHz, 16-bit, 4096 bytes per chunk
_SECONDS_PER_CHUNK = 4096 / 2 / 24_000  # ~0.085 seconds


class StreamingConversation:
    def __init__(
        self,
        websocket: WebSocket,
        transcriber: BaseTranscriber,
        agent: BaseAgent,
        synthesizer: BaseSynthesizer,
        synthesis_queue: asyncio.Queue,
    ) -> None:
        self._ws = websocket
        self._transcriber = transcriber
        self._agent = agent
        self._synthesizer = synthesizer
        self._synthesis_queue = synthesis_queue
        self._is_human_speaking = True
        self._output_task: asyncio.Task | None = None
        self._log = log.bind(component="StreamingConversation")

    async def start(self) -> None:
        """Connect transcriber and start all workers."""
        await self._transcriber.connect()
        self._transcriber.start()
        self._agent.start()
        self._synthesizer.start()
        self._output_task = asyncio.create_task(self._output_loop())
        self._log.info("conversation_started")

    def receive_audio(self, chunk: bytes) -> None:
        """Called by WebSocket receiver for each incoming audio chunk."""
        self._transcriber.send_audio(chunk)

    async def _output_loop(self) -> None:
        """Consume SynthesisResult from queue and send audio to client."""
        while True:
            try:
                result: SynthesisResult = await self._synthesis_queue.get()
                await self._send_speech(result)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._log.error("output_loop_error", error=str(exc), exc_info=True)

    async def _send_speech(self, result: SynthesisResult) -> None:
        """Rate-limited audio delivery with interrupt check. See interrupt-handling.md."""
        self._transcriber.mute()
        self._is_human_speaking = False
        chunk_idx = 0

        try:
            async for chunk_result in result.chunk_generator:
                start_time = time.monotonic()

                # Send audio chunk to client
                await self._ws.send_bytes(chunk_result.chunk)
                chunk_idx += 1

                if chunk_result.is_last_chunk:
                    break

                # Rate-limit: wait for chunk duration before sending next
                elapsed = time.monotonic() - start_time
                await asyncio.sleep(max(_SECONDS_PER_CHUNK - elapsed, 0))
        finally:
            self._is_human_speaking = True
            self._transcriber.unmute()

    async def terminate(self) -> None:
        """Gracefully shut down all workers."""
        if self._output_task and not self._output_task.done():
            self._output_task.cancel()
        self._transcriber.terminate()
        self._agent.terminate()
        self._synthesizer.terminate()
        await asyncio.sleep(0.2)  # Allow queues to drain
        self._log.info("conversation_terminated")
```

---

## Provider Factory

```python
# src/factory.py
import asyncio
from google import genai
from .config import VoiceEngineConfig
from .workers.gemini_transcriber import GeminiTranscriberWorker
from .workers.gemini_synthesizer import GeminiSynthesizerWorker
from .workers.langgraph_agent import LangGraphAgentWorker
from .workers.adk_agent import ADKAgentWorker


class VoiceComponentFactory:
    """Creates voice pipeline components from config."""

    def __init__(self, config: VoiceEngineConfig, client: genai.Client) -> None:
        self._config = config
        self._client = client

    def create_transcriber(self, output_queue: asyncio.Queue) -> GeminiTranscriberWorker:
        return GeminiTranscriberWorker(
            output_queue=output_queue,
            client=self._client,
            model=self._config.gemini_live_model,
        )

    def create_agent_langgraph(
        self, input_queue: asyncio.Queue, output_queue: asyncio.Queue
    ) -> LangGraphAgentWorker:
        return LangGraphAgentWorker(
            input_queue=input_queue,
            output_queue=output_queue,
            google_api_key=self._config.gemini_api_key,
        )

    def create_agent_adk(
        self, input_queue: asyncio.Queue, output_queue: asyncio.Queue
    ) -> ADKAgentWorker:
        return ADKAgentWorker(
            input_queue=input_queue,
            output_queue=output_queue,
        )

    def create_synthesizer(
        self, input_queue: asyncio.Queue, output_queue: asyncio.Queue
    ) -> GeminiSynthesizerWorker:
        return GeminiSynthesizerWorker(
            input_queue=input_queue,
            output_queue=output_queue,
            client=self._client,
            model=self._config.gemini_tts_model,
            voice=self._config.gemini_tts_voice,
        )
```
