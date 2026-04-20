from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agent.query_router import QueryRouter


@pytest.fixture
def router(tmp_path):
    # Empty intents dir — only generic signals apply
    with patch("app.agent.query_router.settings") as mock_settings:
        mock_settings.INTENT_DIR = str(tmp_path)
        yield QueryRouter()


@pytest.fixture
def router_with_intents(tmp_path):
    """Router loaded with two intents that share one keyword ('orders')."""
    yaml_content = """
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
    (tmp_path / "test_intents.yaml").write_text(yaml_content)
    with patch("app.agent.query_router.settings") as mock_settings:
        mock_settings.INTENT_DIR = str(tmp_path)
        yield QueryRouter()


# ── is_data_query tests ───────────────────────────────────────────────────────


def test_sql_keyword_triggers_data_query(router):
    assert router.is_data_query("SELECT * FROM orders") is True


def test_revenue_keyword_triggers_data_query(router):
    assert router.is_data_query("show me total revenue for last quarter") is True


def test_customer_keyword_triggers_data_query(router):
    assert router.is_data_query("find customer with id 123") is True


def test_freeform_chat_not_data_query(router):
    assert router.is_data_query("hello, how are you?") is False


def test_explain_code_not_data_query(router):
    assert (
        router.is_data_query("can you explain what this Python function does?") is False
    )


def test_case_insensitive(router):
    assert router.is_data_query("SHOW REVENUE BY REGION") is True


# ── estimate_intent tests ─────────────────────────────────────────────────────


def test_estimate_single_keyword_match(router_with_intents):
    result = router_with_intents.estimate_intent("show me revenue for Q4")
    assert result.confidence > 0
    assert result.top_intent is not None
    assert result.top_intent.name == "sales_revenue"
    assert result.is_ambiguous is False


def test_estimate_ambiguous_two_matches(router_with_intents):
    # "orders" appears in both intents — scores should be close enough to flag ambiguity
    result = router_with_intents.estimate_intent("show all orders")
    assert result.is_ambiguous is True
    assert result.confidence > 0
    assert len(result.candidates) >= 2


def test_estimate_no_match_zero_confidence(router_with_intents):
    result = router_with_intents.estimate_intent("hello there")
    assert result.confidence == 0.0
    assert result.top_intent is None
    assert result.is_ambiguous is True
    assert result.candidates == []


def test_estimate_candidates_format(router_with_intents):
    result = router_with_intents.estimate_intent("show all orders")
    assert result.is_ambiguous is True
    for candidate in result.candidates:
        assert ": " in candidate, f"Candidate missing ': ' separator: {candidate}"
        name, desc = candidate.split(": ", 1)
        assert name in ("sales_revenue", "customer_data")
        assert len(desc) > 0


def test_estimate_no_intents_loaded(router):
    # Router with empty intent dir — no intents to score against
    result = router.estimate_intent("show revenue data")
    assert result.confidence == 0.0
    assert result.top_intent is None
    assert result.candidates == []
