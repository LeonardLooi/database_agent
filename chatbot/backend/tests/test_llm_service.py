"""Tests for LLMService and LLMProviderFactory."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.ws_messages import MsgIn
from app.services.llm.base import BaseLLMProvider
from app.services.llm.factory import LLMProviderFactory, MODEL_TO_PROVIDER
from app.services.llm_service import LLMService


# ── helpers ───────────────────────────────────────────────────────────────────

def _mock_provider(name: str = "mock", models: list[str] | None = None) -> MagicMock:
    """Return a mock provider with async stream and generate methods."""
    provider = MagicMock(spec=BaseLLMProvider)
    provider.provider_name = name
    provider.default_model = (models or ["mock-model"])[0]
    provider.available_models = models or ["mock-model"]

    async def _stream(*args, **kwargs) -> AsyncGenerator[str, None]:
        for token in ["Hello", " ", "world"]:
            yield token

    provider.stream = _stream
    provider.generate = AsyncMock(return_value="Generated Title")
    return provider


# ── LLMService ────────────────────────────────────────────────────────────────

class TestLLMService:
    @pytest.mark.asyncio
    async def test_stream_yields_tokens(self):
        provider = _mock_provider()
        service = LLMService(provider=provider)
        msgs = [MsgIn(role="user", content="hello")]
        tokens = []
        async for tok in service.stream(msgs, None, 0.7):
            tokens.append(tok)
        assert tokens == ["Hello", " ", "world"]

    @pytest.mark.asyncio
    async def test_stream_uses_default_model_when_none(self):
        provider = _mock_provider(models=["default-model"])
        call_args = {}

        async def _stream(messages, model, temperature, max_tokens=1024):
            call_args["model"] = model
            yield "ok"

        provider.stream = _stream
        service = LLMService(provider=provider)
        async for _ in service.stream([MsgIn(role="user", content="hi")], None, 0.5):
            pass
        assert call_args["model"] == "default-model"

    @pytest.mark.asyncio
    async def test_stream_uses_provided_model(self):
        provider = _mock_provider(models=["model-a", "model-b"])
        call_args = {}

        async def _stream(messages, model, temperature, max_tokens=1024):
            call_args["model"] = model
            yield "ok"

        provider.stream = _stream
        service = LLMService(provider=provider)
        async for _ in service.stream([MsgIn(role="user", content="hi")], "model-b", 0.5):
            pass
        assert call_args["model"] == "model-b"

    @pytest.mark.asyncio
    async def test_generate_title_returns_stripped_title(self):
        provider = _mock_provider()
        provider.generate = AsyncMock(return_value='"User Login Flow"')
        service = LLMService(provider=provider)
        title = await service.generate_title("How do I log in?")
        assert title == "User Login Flow"

    @pytest.mark.asyncio
    async def test_generate_title_falls_back_on_exception(self):
        provider = _mock_provider()
        provider.generate = AsyncMock(side_effect=RuntimeError("API down"))
        service = LLMService(provider=provider)
        title = await service.generate_title("anything")
        assert title == "New Conversation"

    @pytest.mark.asyncio
    async def test_generate_title_uses_last_model(self):
        provider = _mock_provider(models=["fast-model", "slow-model"])
        called_with = {}
        async def _generate(messages, model, max_tokens=20):
            called_with["model"] = model
            return "Test Title"
        provider.generate = _generate
        service = LLMService(provider=provider)
        await service.generate_title("a message")
        assert called_with.get("model") == "slow-model"


# ── LLMProviderFactory ────────────────────────────────────────────────────────

class TestLLMProviderFactory:
    def test_resolve_provider_for_known_model(self):
        assert LLMProviderFactory.resolve_provider_for_model("gpt-4o") == "openai"
        assert LLMProviderFactory.resolve_provider_for_model("claude-opus-4-20250514") == "anthropic"
        assert LLMProviderFactory.resolve_provider_for_model("gemini-2.0-flash") == "gemini"

    def test_resolve_provider_for_unknown_model_returns_none(self):
        assert LLMProviderFactory.resolve_provider_for_model("nonexistent-model") is None

    def test_available_providers_returns_list(self):
        providers = LLMProviderFactory.available_providers()
        assert isinstance(providers, list)

    def test_get_providers_data_returns_list_of_dicts(self):
        data = LLMProviderFactory.get_providers_data()
        assert isinstance(data, list)
        for item in data:
            assert "provider" in item
            assert "models" in item
            assert "default_model" in item

    def test_register_and_create_custom_provider(self):
        class FakeProvider(BaseLLMProvider):
            provider_name = "fake_test"
            available_models = ["fake-1"]
            default_model = "fake-1"

            async def stream(self, messages, model, temperature, max_tokens=1024):
                yield "fake"

            async def generate(self, messages, model, max_tokens=128):
                return "fake"

        LLMProviderFactory.register("fake_test", FakeProvider)
        assert "fake_test" in LLMProviderFactory.available_providers()

        provider = LLMProviderFactory.create("fake_test")
        assert isinstance(provider, FakeProvider)

        # Cleanup
        del LLMProviderFactory._registry["fake_test"]

    def test_create_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMProviderFactory.create("nonexistent_xyz")

    def test_model_to_provider_map_has_required_keys(self):
        assert "gpt-4o" in MODEL_TO_PROVIDER
        assert "claude-sonnet-4-20250514" in MODEL_TO_PROVIDER
        assert "gemini-2.0-flash" in MODEL_TO_PROVIDER
        assert "amazon.nova-pro-v1:0" in MODEL_TO_PROVIDER
