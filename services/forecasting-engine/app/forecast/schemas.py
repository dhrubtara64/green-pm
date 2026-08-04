"""Forecasting Engine schemas — S14-01, S14-03."""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

_FORECAST_DOMAINS: frozenset[str] = frozenset({
    "SCHEDULE", "BUDGET", "QUALITY", "RESOURCE", "COMMISSIONING", "CASH_FLOW"
})
_TREND_DIRECTIONS: frozenset[str] = frozenset({"UP", "DOWN", "STABLE"})


@dataclass(frozen=True)
class ForecastQuery:
    project_id: uuid.UUID
    domain: str

    def __post_init__(self) -> None:
        if self.domain not in _FORECAST_DOMAINS:
            raise ValueError(f"domain must be one of {_FORECAST_DOMAINS}, got {self.domain!r}")


class ForecastDomainCreate(BaseModel):
    project_id: uuid.UUID
    domain: str
    current_value: float
    forecast_value: float
    confidence: float = 0.5
    trend: str = "STABLE"

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if v not in _FORECAST_DOMAINS:
            raise ValueError(f"domain must be one of {_FORECAST_DOMAINS}")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be in [0.0, 1.0]")
        return v

    @field_validator("trend")
    @classmethod
    def validate_trend(cls, v: str) -> str:
        if v not in _TREND_DIRECTIONS:
            raise ValueError(f"trend must be one of {_TREND_DIRECTIONS}")
        return v


class ForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    domain: str
    current_value: float
    forecast_value: float
    confidence: float
    trend: str
    computed_at: Optional[datetime] = None


class ForecastSummaryResponse(BaseModel):
    project_id: uuid.UUID
    domains: list[ForecastResponse]
    total: int
