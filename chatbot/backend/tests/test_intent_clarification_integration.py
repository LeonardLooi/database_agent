from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.clarification_state import ClarificationState
from app.agent.intent_loader import YAMLIntentLoader
from app.agent.query_router import QueryRouter


_INTENTS_YAML = """
intents:
  - name: sales_revenue
    description: Query sales revenue and order totals
    connectors:
      - type: snowflake
    keywords: [revenue, sales, orders, total]
  - name: customer_data
    description: Query customer profiles and contact info
    connectors:
      - type: mssql
    keywords: [customer, contact, profile, orders]
"""


@pytest.fixture
def intent_yaml(tmp_path):
    f = tmp_path / "intents.yaml"
    f.write_text(_INTENTS_YAML)
    return tmp_path


@pytest.fixture
def router_with_intents(intent_yaml):
    with patch("app.agent.query_router.settings") as mock_settings:
        mock_settings.INTENT_DIR = str(intent_yaml)
        yield QueryRouter()


def test_estimate_then_select_known_intent(router_with_intents, clarification_state):
    """Full flow: ambiguous estimation → set_pending → resume resolves matched intent."""
    estimation = router_with_intents.estimate_intent("show all orders")
    assert estimation.is_ambiguous
    assert len(estimation.candidates) >= 2

    clarification_state.set_pending(
        user_id="u1",
        conversation_id="c1",
        question="Which area?",
        candidates=estimation.candidates,
        original_query="show all orders",
        clarification_type="intent_selection",
    )
    assert clarification_state.is_pending("u1", "c1")

    pending = clarification_state.get_pending("u1", "c1")
    assert pending["clarification_type"] == "intent_selection"

    # Simulate user selecting "sales_revenue: Query sales revenue and order totals"
    user_selection = next(
        c for c in pending["candidates"] if c.startswith("sales_revenue")
    )
    selected_name = user_selection.split(": ", 1)[0].strip()

    matched = router_with_intents._loader.get(selected_name)
    assert matched is not None
    assert matched.name == "sales_revenue"

    clarification_state.clear("u1", "c1")
    assert not clarification_state.is_pending("u1", "c1")


def test_resume_with_unknown_selection_goes_freeform(
    router_with_intents, clarification_state
):
    """When user types a selection that doesn't match any intent, matched_intent is None."""
    clarification_state.set_pending(
        user_id="u1",
        conversation_id="c2",
        question="Which area?",
        candidates=["sales_revenue: Q sales", "customer_data: Q customers"],
        original_query="show data",
        clarification_type="intent_selection",
    )

    # Simulate an unrecognised selection
    user_content = "something_unknown: I just typed this"
    selected_name = user_content.split(": ", 1)[0].strip()
    matched = router_with_intents._loader.get(selected_name)

    assert matched is None  # triggers generic LLM path


@pytest.mark.asyncio
async def test_ask_clarification_tool_stores_agent_question_type(clarification_state):
    """Existing ask_clarification tool still defaults to agent_question type."""
    from app.agent.tools.clarification_tools import ask_clarification
    from app.agent.tools.query_tools import AgentToolContext
    from app.agent.dataframe_store import DataFrameStore
    import fakeredis

    fake_ws = AsyncMock()
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    store = DataFrameStore(redis_client=fake_redis)
    cs = ClarificationState(redis_client=fake_redis)

    ctx = AgentToolContext(
        user_id="u1",
        conversation_id="c3",
        store=store,
        clarification_state=cs,
        websocket=fake_ws,
    )

    await ask_clarification(
        "Which database do you want?", ctx, candidates=["snowflake", "bigquery"]
    )

    pending = cs.get_pending("u1", "c3")
    assert pending is not None
    assert pending.get("clarification_type", "agent_question") == "agent_question"
    assert "snowflake" in pending["candidates"]
