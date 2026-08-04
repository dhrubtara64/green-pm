"""Domain schemas for Executive Digital Twin + Command Centre — S17-02, S17-03, S17-04."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

# EDT: 3 synthesis panels populated every Monday 06:00
EDT_PANELS: frozenset[str] = frozenset({
    "REALITY",
    "FORECAST",
    "REQUIRED_DECISIONS",
})

# Command Centre: 8 real-time panels updated on engine events — S17-03
COMMAND_CENTRE_PANELS: frozenset[str] = frozenset({
    "RISKS",
    "DEPENDENCIES",
    "VENDORS",
    "READINESS",
    "FORECASTS",
    "DECISIONS",
    "ALIGNMENT",
    "SIMULATIONS",
})

COMMAND_CENTRE_PANEL_COUNT: int = 8


@dataclass(frozen=True)
class EDTSynthesisSpec:
    """Immutable specification for one EDT synthesis run."""

    project_id: uuid.UUID
    synthesis_date: date
    panels: dict  # {panel_name: dict}

    def __post_init__(self) -> None:
        if not self.panels:
            raise ValueError("panels cannot be empty")
        invalid = set(self.panels.keys()) - EDT_PANELS
        if invalid:
            raise ValueError(f"Invalid EDT panel(s): {invalid}")


@dataclass(frozen=True)
class CommandCentreUpdate:
    """Immutable record of a single panel update triggered by an engine event."""

    project_id: uuid.UUID
    panel_name: str
    panel_data: dict
    triggered_by_event: Optional[str]

    def __post_init__(self) -> None:
        if self.panel_name not in COMMAND_CENTRE_PANELS:
            raise ValueError(f"Invalid Command Centre panel: {self.panel_name!r}")


class EDTSynthesisCreate(BaseModel):
    project_id: uuid.UUID
    synthesis_date: date
    reality_panel: dict = {}
    forecast_panel: dict = {}
    decisions_panel: dict = {}


class EDTSynthesisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    synthesis_date: date
    reality_panel: dict = {}
    forecast_panel: dict = {}
    decisions_panel: dict = {}
    synthesized_at: Optional[datetime] = None


class CommandCentrePanelCreate(BaseModel):
    project_id: uuid.UUID
    panel_name: str
    panel_data: dict = {}
    triggered_by_event: Optional[str] = None

    @field_validator("panel_name")
    @classmethod
    def validate_panel_name(cls, v: str) -> str:
        if v not in COMMAND_CENTRE_PANELS:
            raise ValueError(
                f"Invalid panel_name: {v!r}. Must be one of {sorted(COMMAND_CENTRE_PANELS)}"
            )
        return v


class CommandCentrePanelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    panel_name: str
    panel_data: dict = {}
    updated_at: Optional[datetime] = None
    triggered_by_event: Optional[str] = None
