from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from app.agent.intent_loader import YAMLIntentLoader


def _write_intent(tmp_path: Path, name: str, content: dict) -> None:
    f = tmp_path / f"{name}.yaml"
    f.write_text(yaml.dump(content))


def test_loads_valid_intent(tmp_path):
    _write_intent(
        tmp_path,
        "sales",
        {
            "intents": [
                {
                    "name": "sales_revenue",
                    "description": "Sales data",
                    "connectors": [{"type": "snowflake"}],
                    "prompt_file": "sales_revenue.md",
                    "keywords": ["revenue", "sales"],
                }
            ]
        },
    )
    loader = YAMLIntentLoader(str(tmp_path))
    intents = loader.all_intents()
    assert len(intents) == 1
    assert intents[0].name == "sales_revenue"
    assert "revenue" in intents[0].keywords


def test_multiple_files_merged(tmp_path):
    _write_intent(tmp_path, "a", {"intents": [{"name": "ia", "description": "a", "connectors": [{"type": "snowflake"}], "prompt_file": "a.md"}]})
    _write_intent(tmp_path, "b", {"intents": [{"name": "ib", "description": "b", "connectors": [{"type": "bigquery"}], "prompt_file": "b.md"}]})
    loader = YAMLIntentLoader(str(tmp_path))
    names = loader.all_names()
    assert "ia" in names
    assert "ib" in names


def test_empty_directory(tmp_path):
    loader = YAMLIntentLoader(str(tmp_path))
    assert loader.all_intents() == []


def test_missing_required_field_raises(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("intents:\n  - name: x\n")  # missing description, connectors, prompt_file
    with pytest.raises(Exception):
        YAMLIntentLoader(str(tmp_path))
