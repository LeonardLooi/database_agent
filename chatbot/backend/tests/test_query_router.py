from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.agent.query_router import QueryRouter


@pytest.fixture
def router(tmp_path):
    # Empty intents dir — only generic signals apply
    with patch("app.agent.query_router.settings") as mock_settings:
        mock_settings.INTENT_DIR = str(tmp_path)
        yield QueryRouter()


def test_sql_keyword_triggers_data_query(router):
    assert router.is_data_query("SELECT * FROM orders") is True


def test_revenue_keyword_triggers_data_query(router):
    assert router.is_data_query("show me total revenue for last quarter") is True


def test_customer_keyword_triggers_data_query(router):
    assert router.is_data_query("find customer with id 123") is True


def test_freeform_chat_not_data_query(router):
    assert router.is_data_query("hello, how are you?") is False


def test_explain_code_not_data_query(router):
    assert router.is_data_query("can you explain what this Python function does?") is False


def test_case_insensitive(router):
    assert router.is_data_query("SHOW REVENUE BY REGION") is True
