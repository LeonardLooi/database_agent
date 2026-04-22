"""Phase 2 — SkillRegistry unit tests."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest

from app.agent.skill_registry import SkillRegistry, SkillSchema


# ── helpers ───────────────────────────────────────────────────────────────────

_VALID_YAML = dedent("""\
    name: test_skill
    description: A test skill for unit tests.
    instructions: |
      Step 1: do something.
      Step 2: done.
    parameters:
      input_text:
        type: string
        required: true
        description: The text to process
    output_format: |
      {"result": "..."}
    tags: [test, unit]
""")

_INVALID_YAML = "name: [this is: invalid yaml: {"


def _make_registry(tmp_path: Path, yaml_content: str | None = None) -> SkillRegistry:
    """Return a SkillRegistry pointed at tmp_path, optionally with one YAML file."""
    if yaml_content is not None:
        (tmp_path / "test_skill.yaml").write_text(yaml_content)
    with patch.object(SkillRegistry, "_start_watcher"):
        return SkillRegistry(tmp_path)


# ── tests ─────────────────────────────────────────────────────────────────────


def test_loads_valid_yaml_skill(tmp_path):
    """A well-formed YAML file is parsed into a SkillSchema."""
    registry = _make_registry(tmp_path, _VALID_YAML)
    assert "test_skill" in registry.list_skills()
    skill = registry.get_skill("test_skill")
    assert isinstance(skill, SkillSchema)
    assert skill.description == "A test skill for unit tests."
    assert "input_text" in skill.parameters


def test_invalid_yaml_skipped_with_warning(tmp_path, caplog):
    """An invalid YAML file is skipped and logged as WARNING; registry still loads."""
    import logging

    (tmp_path / "bad.yaml").write_text(_INVALID_YAML)
    with patch.object(SkillRegistry, "_start_watcher"):
        with caplog.at_level(logging.WARNING):
            registry = SkillRegistry(tmp_path)

    assert registry.list_skills() == []


def test_missing_skills_dir_logs_warning(tmp_path, caplog):
    """A non-existent skills directory is logged as WARNING; no crash."""
    import logging

    nonexistent = tmp_path / "does_not_exist"
    with patch.object(SkillRegistry, "_start_watcher"):
        with caplog.at_level(logging.WARNING):
            registry = SkillRegistry(nonexistent)

    assert registry.list_skills() == []


def test_get_all_descriptions_returns_names_and_descriptions(tmp_path):
    """get_all_descriptions() contains skill names and their descriptions."""
    registry = _make_registry(tmp_path, _VALID_YAML)
    desc = registry.get_all_descriptions()
    assert "test_skill" in desc
    assert "A test skill" in desc


@pytest.mark.asyncio
async def test_reload_updates_registry(tmp_path):
    """After hot-reload, newly added skills appear in the registry."""
    registry = _make_registry(tmp_path)
    assert registry.list_skills() == []

    (tmp_path / "test_skill.yaml").write_text(_VALID_YAML)
    await registry.reload()

    assert "test_skill" in registry.list_skills()
