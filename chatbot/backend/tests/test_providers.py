"""Phase 7 — Provider execute_skill() and SkillPromptBuilder tests."""
from __future__ import annotations

from textwrap import dedent
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.skill_prompt_builder import SkillPromptBuilder
from app.agent.skill_registry import SkillParameter, SkillSchema
from app.services.llm.base import BaseLLMProvider, RoutingDecision, SkillResult


# ── shared fixture ────────────────────────────────────────────────────────────

def _make_skill(output_format: str = '{"result": "..."}') -> SkillSchema:
    return SkillSchema(
        name="test_skill",
        description="A test skill.",
        instructions="You are a test assistant. Answer precisely.",
        parameters={
            "query": SkillParameter(type="string", required=True, description="Input query"),
        },
        output_format=output_format,
        tags=["test"],
    )


# ── SkillPromptBuilder ────────────────────────────────────────────────────────


def test_prompt_builder_includes_instructions_params_output():
    skill = _make_skill()
    prompt = SkillPromptBuilder.build(skill, {"query": "hello world"})

    assert "You are a test assistant" in prompt
    assert "query: hello world" in prompt
    assert '{"result": "..."}' in prompt


def test_prompt_builder_omits_param_block_when_empty():
    skill = _make_skill()
    prompt = SkillPromptBuilder.build(skill, {})

    assert "Input parameters" not in prompt
    assert "You are a test assistant" in prompt


# ── BaseLLMProvider raises NotImplementedError ────────────────────────────────


@pytest.mark.asyncio
async def test_base_execute_skill_raises():
    class _Minimal(BaseLLMProvider):
        provider_name = "minimal"
        default_model = "m"
        available_models = ["m"]
        def stream(self, *a, **kw): ...
        async def generate(self, *a, **kw): return ""

    provider = _Minimal()
    with pytest.raises(NotImplementedError):
        await provider.execute_skill("s", "msg", _make_skill(), {}, "m")


# ── OpenAIProvider.execute_skill() ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_openai_execute_skill_returns_skill_result():
    skill = _make_skill()
    fake_response = MagicMock()
    fake_response.choices[0].message.content = '{"result": "42"}'

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        from app.services.llm.providers.openai_provider import OpenAIProvider
        with patch("openai.AsyncOpenAI"):
            provider = OpenAIProvider.__new__(OpenAIProvider)
            provider._client = MagicMock()
            provider._client.chat.completions.create = AsyncMock(return_value=fake_response)

            result = await provider.execute_skill(
                session_id="s1",
                user_message="run the test",
                skill=skill,
                params={"query": "hello"},
                model="gpt-4o",
            )

    assert isinstance(result, SkillResult)
    assert result.routing_decision == RoutingDecision.CALL_SKILL
    assert result.skill_name == "test_skill"
    assert result.parsed_output == {"result": "42"}


# ── AnthropicProvider.execute_skill() ────────────────────────────────────────


@pytest.mark.asyncio
async def test_anthropic_execute_skill_returns_skill_result():
    skill = _make_skill(output_format="")  # free-text skill
    fake_response = MagicMock()
    fake_response.content[0].text = "Here is the answer."

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = "sk-ant-test"
        from app.services.llm.providers.anthropic_provider import AnthropicProvider
        with patch("anthropic.AsyncAnthropic"):
            provider = AnthropicProvider.__new__(AnthropicProvider)
            provider._client = MagicMock()
            provider._client.messages.create = AsyncMock(return_value=fake_response)

            result = await provider.execute_skill(
                session_id="s1",
                user_message="answer the question",
                skill=skill,
                params={},
                model="claude-sonnet-4-20250514",
            )

    assert isinstance(result, SkillResult)
    assert result.output == "Here is the answer."
    assert result.parsed_output is None   # free-text → no JSON parse
    assert result.routing_decision == RoutingDecision.CALL_SKILL
