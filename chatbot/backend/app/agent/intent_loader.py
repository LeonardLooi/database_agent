from __future__ import annotations

import glob
from pathlib import Path
from typing import Literal

import structlog
import yaml
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger()


class ConnectorConfig(BaseModel):
    type: Literal["snowflake", "bigquery", "mssql", "rest"]
    # DB connector fields
    warehouse: str = ""
    database: str = ""
    schema_name: str = Field(default="PUBLIC", alias="schema")
    project_id: str = ""
    server: str = ""
    # REST connector fields
    url: str = ""
    method: str = "POST"
    headers: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class IntentDefinition(BaseModel):
    name: str
    description: str
    connectors: list[ConnectorConfig] = Field(default_factory=list)
    prompt_file: str = ""
    keywords: list[str] = Field(default_factory=list)
    requires_combine: bool = False

    @field_validator("name")
    @classmethod
    def name_no_spaces(cls, v: str) -> str:
        if " " in v:
            raise ValueError(f"Intent name must not contain spaces: '{v}'")
        return v

    @field_validator("connectors")
    @classmethod
    def at_least_one_connector(cls, v: list[ConnectorConfig]) -> list[ConnectorConfig]:
        if not v:
            raise ValueError("Intent must define at least one connector")
        return v


class YAMLIntentLoader:
    """Loads and validates all intent YAML files from the intent directory on startup."""

    def __init__(self, intent_dir: str) -> None:
        self._dir = Path(intent_dir)
        self._intents: dict[str, IntentDefinition] = {}
        self._load()

    def _load(self) -> None:
        pattern = str(self._dir / "*.yaml")
        files = glob.glob(pattern)
        if not files:
            logger.warning("intent_loader_no_files", directory=str(self._dir))
            return

        for filepath in files:
            try:
                with open(filepath) as f:
                    data = yaml.safe_load(f)

                raw_intents: list[dict] = data.get("intents", [])
                for raw in raw_intents:
                    intent = IntentDefinition.model_validate(raw)
                    if intent.name in self._intents:
                        raise ValueError(
                            f"Duplicate intent name '{intent.name}' in {filepath}"
                        )
                    self._intents[intent.name] = intent

                logger.info("intent_loader_loaded", file=filepath, count=len(raw_intents))
            except Exception as exc:
                # Fail fast — malformed intent config must not silently pass
                logger.error("intent_loader_failed", file=filepath, error=str(exc))
                raise RuntimeError(
                    f"Failed to load intent file '{filepath}': {exc}"
                ) from exc

        logger.info("intent_loader_ready", total=len(self._intents))

    def get(self, name: str) -> IntentDefinition | None:
        return self._intents.get(name)

    def all_intents(self) -> list[IntentDefinition]:
        return list(self._intents.values())

    def all_names(self) -> list[str]:
        return list(self._intents.keys())

    def all_keywords(self) -> dict[str, list[str]]:
        return {name: intent.keywords for name, intent in self._intents.items()}
