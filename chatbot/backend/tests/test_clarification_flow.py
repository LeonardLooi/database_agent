from __future__ import annotations

import pytest

from app.agent.clarification_state import ClarificationState


def test_set_and_get_pending(clarification_state):
    clarification_state.set_pending(
        user_id="u1",
        conversation_id="c1",
        question="Which database?",
        candidates=["sales", "crm"],
        original_query="show me the numbers",
    )
    assert clarification_state.is_pending("u1", "c1")
    pending = clarification_state.get_pending("u1", "c1")
    assert pending["question"] == "Which database?"
    assert "sales" in pending["candidates"]
    assert pending["original_query"] == "show me the numbers"


def test_clear_removes_state(clarification_state):
    clarification_state.set_pending("u1", "c1", "Q?", [], "orig")
    clarification_state.clear("u1", "c1")
    assert not clarification_state.is_pending("u1", "c1")
    assert clarification_state.get_pending("u1", "c1") is None


def test_not_pending_by_default(clarification_state):
    assert not clarification_state.is_pending("u1", "no_conv")


def test_different_conversations_isolated(clarification_state):
    clarification_state.set_pending("u1", "conv_a", "Q?", [], "orig_a")
    assert clarification_state.is_pending("u1", "conv_a")
    assert not clarification_state.is_pending("u1", "conv_b")


def test_set_pending_with_intent_type(clarification_state):
    clarification_state.set_pending(
        user_id="u1",
        conversation_id="c1",
        question="Which area?",
        candidates=["sales_revenue: Query sales", "customer_data: Query customers"],
        original_query="show me the data",
        clarification_type="intent_selection",
    )
    pending = clarification_state.get_pending("u1", "c1")
    assert pending["clarification_type"] == "intent_selection"
    assert len(pending["candidates"]) == 2


def test_set_pending_defaults_to_agent_question(clarification_state):
    clarification_state.set_pending(
        user_id="u1",
        conversation_id="c2",
        question="Which DB?",
        candidates=[],
        original_query="query something",
    )
    pending = clarification_state.get_pending("u1", "c2")
    assert pending["clarification_type"] == "agent_question"
