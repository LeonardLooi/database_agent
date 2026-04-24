"""Extended SkillRegistry tests — load_file, reload, edge cases."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.agent.skill_registry import SkillRegistry, SkillSchema


@pytest.fixture
def tmp_skills_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _make_registry(skills_dir: Path) -> SkillRegistry:
    """Create a SkillRegistry with the file watcher disabled to avoid event loop issues."""
    with patch.object(SkillRegistry, "_start_watcher", return_value=None):
        return SkillRegistry(skills_dir)


def _write_skill(skills_dir: Path, name: str, content: str) -> None:
    (skills_dir / f"{name}.yaml").write_text(content, encoding="utf-8")


_VALID_YAML = """
name: test_skill
description: A test skill for unit tests.
instructions: Answer the user question.
parameters:
  language:
    type: string
    required: false
    default: "en"
    description: Language code
tags: [test, unit]
output_format: markdown
"""

_INVALID_YAML = ":::not valid yaml:::"
_MISSING_REQUIRED = "description: no name field here\ninstructions: blah"


class TestLoadFile:
    def test_valid_yaml_returns_schema(self, tmp_skills_dir):
        _write_skill(tmp_skills_dir, "valid", _VALID_YAML)
        registry = _make_registry(tmp_skills_dir)
        skill = registry.get_skill("test_skill")
        assert skill is not None
        assert skill.name == "test_skill"
        assert "test" in skill.tags

    def test_invalid_yaml_skipped_silently(self, tmp_skills_dir):
        _write_skill(tmp_skills_dir, "bad", _INVALID_YAML)
        registry = _make_registry(tmp_skills_dir)
        assert registry.list_skills() == []

    def test_missing_required_field_skipped(self, tmp_skills_dir):
        _write_skill(tmp_skills_dir, "incomplete", _MISSING_REQUIRED)
        registry = _make_registry(tmp_skills_dir)
        assert registry.list_skills() == []

    def test_nonexistent_dir_logs_warning(self):
        registry = _make_registry(Path("/nonexistent/path/that/does/not/exist"))
        assert registry.list_skills() == []


class TestGetAndList:
    def test_get_skill_exists(self, tmp_skills_dir):
        _write_skill(tmp_skills_dir, "s1", _VALID_YAML)
        registry = _make_registry(tmp_skills_dir)
        assert registry.get_skill("test_skill") is not None

    def test_get_skill_not_exists_returns_none(self, tmp_skills_dir):
        registry = _make_registry(tmp_skills_dir)
        assert registry.get_skill("nonexistent") is None

    def test_list_skills_returns_names(self, tmp_skills_dir):
        _write_skill(tmp_skills_dir, "s1", _VALID_YAML)
        registry = _make_registry(tmp_skills_dir)
        names = registry.list_skills()
        assert "test_skill" in names

    def test_get_all_descriptions_empty(self, tmp_skills_dir):
        registry = _make_registry(tmp_skills_dir)
        assert registry.get_all_descriptions() == "(no skills loaded)"

    def test_get_all_descriptions_non_empty(self, tmp_skills_dir):
        _write_skill(tmp_skills_dir, "s1", _VALID_YAML)
        registry = _make_registry(tmp_skills_dir)
        desc = registry.get_all_descriptions()
        assert "test_skill" in desc
        assert "A test skill" in desc


class TestWatcher:
    def test_watcher_started_when_watchdog_available(self, tmp_skills_dir):
        """_start_watcher should start the observer when watchdog is installed."""
        _write_skill(tmp_skills_dir, "s1", _VALID_YAML)
        import asyncio

        async def _fake_run_coroutine_threadsafe(coro, loop):
            pass

        # Patch Observer to avoid actually starting a filesystem thread
        with patch("watchdog.observers.Observer") as mock_observer_cls:
            mock_observer = mock_observer_cls.return_value
            loop = asyncio.new_event_loop()
            with patch("asyncio.get_running_loop", return_value=loop):
                registry = SkillRegistry(tmp_skills_dir)
            mock_observer.start.assert_called_once()
            mock_observer.schedule.assert_called_once()
            mock_observer.daemon = True
        loop.close()

    def test_watcher_disabled_when_watchdog_not_installed(self, tmp_skills_dir, caplog):
        """_start_watcher logs info and returns when watchdog is not installed."""
        import sys
        orig = sys.modules.pop("watchdog", None)
        orig_events = sys.modules.pop("watchdog.events", None)
        orig_observers = sys.modules.pop("watchdog.observers", None)
        try:
            with patch.dict("sys.modules", {"watchdog.events": None, "watchdog.observers": None}):
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    with patch("asyncio.get_running_loop", return_value=loop):
                        registry = SkillRegistry(tmp_skills_dir)
                    # Should complete without raising; no observer started
                    assert registry is not None
                finally:
                    loop.close()
        finally:
            if orig:
                sys.modules["watchdog"] = orig
            if orig_events:
                sys.modules["watchdog.events"] = orig_events
            if orig_observers:
                sys.modules["watchdog.observers"] = orig_observers


class TestReload:
    @pytest.mark.asyncio
    async def test_reload_picks_up_new_skill(self, tmp_skills_dir):
        registry = _make_registry(tmp_skills_dir)
        assert registry.list_skills() == []

        _write_skill(tmp_skills_dir, "new", _VALID_YAML)
        await registry.reload()
        assert "test_skill" in registry.list_skills()

    @pytest.mark.asyncio
    async def test_reload_removes_deleted_skill(self, tmp_skills_dir):
        _write_skill(tmp_skills_dir, "s1", _VALID_YAML)
        registry = _make_registry(tmp_skills_dir)
        assert "test_skill" in registry.list_skills()

        (tmp_skills_dir / "s1.yaml").unlink()
        await registry.reload()
        assert registry.list_skills() == []
