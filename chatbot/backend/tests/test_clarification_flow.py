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
