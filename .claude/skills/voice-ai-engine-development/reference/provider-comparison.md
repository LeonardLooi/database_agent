# Provider Comparison — Voice AI Engine

Gemini is the PRIMARY provider for this workspace. This guide positions alternatives clearly and defines when to use each.

---

## Primary Recommendation: Full Gemini Pipeline

For new voice AI projects in this workspace, the default is:

| Component | Provider | Model |
|-----------|----------|-------|
| STT (real-time) | Gemini Live API | `gemini-live-2.5-flash-native-audio` |
| Agent LLM | Gemini (via LangGraph or ADK) | `gemini-2.5-flash` |
| TTS | Gemini TTS | `gemini-2.5-flash-tts-preview` |

This pipeline:
- Uses a single API key (`GEMINI_API_KEY`)
- Has native barge-in — no custom VAD required
- Supports 70+ languages across TTS
- Delivers ~600ms end-to-end latency
- Integrates directly with LangGraph and Google ADK

---

## STT / Transcription Provider Comparison

### Gemini Live API (PRIMARY)

**Model:** `gemini-live-2.5-flash-native-audio`

**Strengths:**
- Native barge-in (VAD built-in — no custom interrupt detection)
- Emotion/affect-aware transcription
- Multimodal: accepts audio + camera simultaneously
- ~600ms latency end-to-end (STT + response)
- Single API key with the rest of the Gemini stack
- 70+ language support

**Weaknesses:**
- Sessions expire (~30 min) — must implement reconnect
- WebSocket-only — more complex than HTTP
- Accuracy may trail Deepgram on accented English

**Use Gemini Live when:** building a new voice AI on this workspace's stack; you want native barge-in; you need multimodal input; you want one API key.

---

### Deepgram

**Strengths:**
- Fastest STT: ~200–300ms latency
- Highest English accuracy (95%+) — outperforms most providers on clear audio
- Excellent streaming support
- $0.0043/minute

**Weaknesses:**
- Requires separate API key and SDK (`deepgram-sdk`)
- No native barge-in — must implement custom VAD
- Weaker on non-English accents

**Use Deepgram when:** accuracy on English is the top priority; latency must be below 300ms; you already have Deepgram infrastructure.

---

### AssemblyAI

**Strengths:**
- Highest accuracy on accented speech (96%+)
- Strong speaker diarization
- $0.00025/second

**Weaknesses:**
- Higher latency than Deepgram
- No native barge-in

**Use AssemblyAI when:** application serves a diverse user base with varied accents; multi-speaker diarization is required.

---

### Azure Speech

**Strengths:**
- Enterprise SLA
- 100+ language support
- Compliance-ready (SOC2, HIPAA)

**Weaknesses:**
- Higher cost ($1/hour)
- Slower than Deepgram
- Requires Azure account

**Use Azure Speech when:** enterprise compliance is mandatory; infrastructure is already on Azure.

---

## TTS Provider Comparison

### Gemini TTS (PRIMARY)

**Models:**
- `gemini-2.5-flash-tts-preview` — fast, low cost, good quality
- `gemini-2.5-pro-tts-preview` — high fidelity, slower, higher cost

**Strengths:**
- 70+ language support
- Style control via natural language (no SSML needed)
- Multi-speaker synthesis in one call
- Emotion-aware synthesis
- 5–8 preset voices: Aoede, Lyra, Orion, and others
- Single API key with Gemini Live

**Weaknesses:**
- Fewer voice customization options vs ElevenLabs
- No voice cloning

**Use Gemini TTS when:** building on the Gemini stack; multi-language required; you want style control without SSML.

---

### ElevenLabs

**Strengths:**
- Most natural-sounding voices
- Voice cloning
- Strong emotional range

**Weaknesses:**
- $0.30/1k characters (most expensive)
- Rate limits on lower tiers
- Separate API key

**Use ElevenLabs when:** maximum voice naturalness is the product differentiator; voice cloning is required.

---

### Azure TTS

**Strengths:**
- Enterprise SLA
- 100+ languages
- $4–16/1M characters

**Weaknesses:**
- Less natural than Gemini or ElevenLabs
- Requires Azure account

**Use Azure TTS when:** enterprise Azure infrastructure; compliance-sensitive; high-volume cost reduction.

---

### Amazon Polly / Google Cloud TTS

**Use when:** AWS/GCP infrastructure lock-in; cost-sensitive high-volume; legacy compatibility.

---

## Agent LLM Comparison

### Gemini via LangGraph or ADK (PRIMARY)

**Models:** `gemini-2.5-flash` (default), `gemini-2.5-pro` (higher quality)

**Best for:** integrated Gemini stack; ADK agent patterns; multimodal reasoning.

---

### OpenAI GPT-4

**Best for:** highest conversational quality; instruction following; complex reasoning.
**Cost:** $0.01–0.03/1k tokens.

---

### Anthropic Claude

**Best for:** safety-critical applications; long-context conversations; nuanced reasoning.
**Cost:** $0.003–0.015/1k tokens.

---

## Decision Matrix

| Priority | Transcriber | TTS | Agent |
|----------|-------------|-----|-------|
| **Default (this workspace)** | Gemini Live | Gemini TTS Flash | Gemini (LangGraph/ADK) |
| **Lowest Latency** | Deepgram | Gemini TTS Flash | Gemini Flash |
| **Highest Accuracy** | AssemblyAI | ElevenLabs | GPT-4 |
| **Voice Quality** | Gemini Live | ElevenLabs | GPT-4 |
| **Enterprise/Compliance** | Azure Speech | Azure TTS | OpenAI |
| **Multi-language** | Gemini Live | Gemini TTS | Gemini |
| **Voice Cloning** | Any | ElevenLabs | Any |

---

## Recommended Stack Configurations

### Default — Gemini End-to-End

```python
config = {
    "gemini_live_model": "gemini-live-2.5-flash-native-audio",
    "gemini_tts_model": "gemini-2.5-flash-tts-preview",
    "gemini_tts_voice": "Aoede",
    "agent_model": "gemini-2.5-flash",
}
```

Estimated cost: ~$0.005–0.01 per minute of conversation.

---

### High Accuracy English

```python
config = {
    "transcriber": "deepgram",       # ~300ms, highest English accuracy
    "deepgram_model": "nova-2",
    "gemini_tts_model": "gemini-2.5-flash-tts-preview",
    "agent": "openai",               # GPT-4 for highest response quality
    "openai_model": "gpt-4o",
}
```

Estimated cost: ~$0.03–0.05 per minute.

---

### Premium Voice Experience

```python
config = {
    "transcriber": "deepgram",
    "tts": "elevenlabs",             # Most natural voices
    "agent": "openai",
}
```

Estimated cost: ~$0.05–0.08 per minute.

---

### Switching Providers

The `VoiceComponentFactory` pattern makes provider switching a config change — no pipeline code changes needed. See `reference/worker-pipeline.md` § Provider Factory.

```python
# All provider selection is in config — factory reads it
factory = VoiceComponentFactory(config=VoiceEngineConfig(), client=gemini_client)
transcriber = factory.create_transcriber(output_queue)
agent = factory.create_agent_langgraph(input_queue, output_queue)
synthesizer = factory.create_synthesizer(input_queue, output_queue)
```
