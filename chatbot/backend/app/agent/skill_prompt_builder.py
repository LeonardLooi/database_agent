from __future__ import annotations

from app.agent.skill_registry import SkillSchema


class SkillPromptBuilder:
    """Assembles a complete LLM prompt from a YAML skill definition and resolved parameters.

    This is a static helper — it carries no state and has no dependency on any provider.
    The resulting prompt is sent as the system instruction to whichever provider executes it.
    """

    @staticmethod
    def build(skill: SkillSchema, params: dict) -> str:
        parts = [skill.instructions.strip()]

        if params:
            param_lines = "\n".join(f"  {k}: {v}" for k, v in params.items())
            parts.append(f"Input parameters:\n{param_lines}")

        if skill.output_format:
            parts.append(
                f"Respond using ONLY this exact JSON format:\n{skill.output_format.strip()}"
            )

        return "\n\n".join(parts)
