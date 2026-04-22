from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger()


class SkillParameter(BaseModel):
    type: str
    required: bool = False
    default: Any = None
    description: str = ""


class SkillSchema(BaseModel):
    name: str
    description: str
    instructions: str
    parameters: dict[str, SkillParameter] = {}
    output_format: str = ""
    tags: list[str] = []


class SkillRegistry:
    """Loads and maintains the in-memory YAML skill registry.

    Skills are loaded from *.yaml files in the skills directory at startup.
    In dev mode (watchdog installed), files are watched for hot-reload.
    Invalid YAML files are logged as WARNING and skipped; they do not block startup.

    The two response paths in this system are intentionally separate:
    - SkillResult (from execute_skill): YAML-driven NLP and document tasks
    - AgentLoopResult (from run_agent_loop): database agent tool-use with SQL execution
    Merging them would require many optional fields and confuse the two distinct flows.
    """

    def __init__(self, skills_dir: str | Path) -> None:
        self._dir = Path(skills_dir)
        self._skills: dict[str, SkillSchema] = {}
        self._lock = asyncio.Lock()
        self._load_all()
        self._start_watcher()

    def _load_all(self) -> None:
        skills: dict[str, SkillSchema] = {}
        if not self._dir.exists():
            logger.warning("skills_dir_not_found", path=str(self._dir))
            self._skills = skills
            return

        for yaml_file in self._dir.glob("*.yaml"):
            skill = self._load_file(yaml_file)
            if skill:
                skills[skill.name] = skill

        logger.info("skills_loaded", count=len(skills), dir=str(self._dir))
        self._skills = skills

    def _load_file(self, path: Path) -> SkillSchema | None:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            return SkillSchema.model_validate(raw)
        except (yaml.YAMLError, ValidationError, OSError) as exc:
            logger.warning("skill_load_failed", file=str(path), error=str(exc))
            return None

    def _start_watcher(self) -> None:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            logger.info("skills_watcher_disabled", reason="watchdog not installed")
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        registry = self

        class _Handler(FileSystemEventHandler):  # type: ignore[misc]
            def on_any_event(self, event: Any) -> None:
                if not event.is_directory and str(event.src_path).endswith(".yaml"):
                    asyncio.run_coroutine_threadsafe(registry.reload(), loop)

        observer = Observer()
        observer.schedule(_Handler(), str(self._dir), recursive=False)
        observer.daemon = True
        observer.start()
        logger.info("skills_watcher_started", dir=str(self._dir))

    async def reload(self) -> None:
        async with self._lock:
            self._load_all()
            logger.info("skills_reloaded", count=len(self._skills))

    def get_skill(self, name: str) -> SkillSchema | None:
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        return list(self._skills)

    def get_all_descriptions(self) -> str:
        if not self._skills:
            return "(no skills loaded)"
        lines = [
            f"- {name}: {skill.description.strip()}"
            for name, skill in self._skills.items()
        ]
        return "\n".join(lines)
