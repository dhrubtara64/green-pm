"""Runbook schema and builder — S18-05."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.monitoring.slo import ENGINE_NAMES, ENGINE_COUNT

RUNBOOK_SECTIONS: tuple[str, ...] = (
    "OVERVIEW",
    "ARCHITECTURE",
    "SLO_THRESHOLDS",
    "ALERT_PLAYBOOK",
    "ESCALATION_PATH",
    "ROLLBACK_STEPS",
)

SECTION_COUNT: int = len(RUNBOOK_SECTIONS)


@dataclass(frozen=True)
class RunbookSpec:
    engine_name: str
    title: str
    version: str
    sections: frozenset[str]
    on_call_team: str

    def __post_init__(self) -> None:
        if self.engine_name not in ENGINE_NAMES:
            raise ValueError(f"Unknown engine: '{self.engine_name}'")
        if not self.title or not self.title.strip():
            raise ValueError("title must be non-empty")
        unknown = self.sections - frozenset(RUNBOOK_SECTIONS)
        if unknown:
            raise ValueError(f"Unknown sections: {unknown}")
        if not self.on_call_team or not self.on_call_team.strip():
            raise ValueError("on_call_team must be non-empty")

    @property
    def is_complete(self) -> bool:
        return frozenset(RUNBOOK_SECTIONS).issubset(self.sections)


def build_runbook(
    engine_name: str,
    version: str = "1.0.0",
    on_call_team: str = "platform-oncall",
) -> RunbookSpec:
    if engine_name not in ENGINE_NAMES:
        raise ValueError(f"Unknown engine: '{engine_name}'")
    title = f"{engine_name.replace('-', ' ').title()} — Operations Runbook"
    return RunbookSpec(
        engine_name=engine_name,
        title=title,
        version=version,
        sections=frozenset(RUNBOOK_SECTIONS),
        on_call_team=on_call_team,
    )


def build_all_runbooks(
    version: str = "1.0.0", on_call_team: str = "platform-oncall"
) -> list[RunbookSpec]:
    return [
        build_runbook(engine, version=version, on_call_team=on_call_team)
        for engine in sorted(ENGINE_NAMES)
    ]


def runbook_index(runbooks: list[RunbookSpec]) -> dict[str, str]:
    return {rb.engine_name: rb.title for rb in runbooks}


def validate_runbook_coverage(runbooks: list[RunbookSpec]) -> list[str]:
    """Return engine names missing a runbook."""
    covered = {rb.engine_name for rb in runbooks}
    return sorted(ENGINE_NAMES - covered)
