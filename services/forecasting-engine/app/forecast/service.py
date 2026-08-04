"""Forecasting Engine service layer — S14-01, S14-03."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.forecast.model import ForecastRecord
from app.forecast.schemas import ForecastDomainCreate


class ForecastNotFoundError(Exception):
    pass


async def upsert_forecast(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    domain: str,
    current_value: float,
    forecast_value: float,
    confidence: float,
    trend: str,
) -> ForecastRecord:
    stmt = select(ForecastRecord).where(
        ForecastRecord.tenant_id == tenant_id,
        ForecastRecord.project_id == project_id,
        ForecastRecord.domain == domain,
    )
    existing = await session.scalar(stmt)
    now = datetime.now(timezone.utc)
    if existing is not None:
        existing.current_value = current_value
        existing.forecast_value = forecast_value
        existing.confidence = confidence
        existing.trend = trend
        existing.computed_at = now
        await session.flush()
        return existing
    record = ForecastRecord(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        domain=domain,
        current_value=current_value,
        forecast_value=forecast_value,
        confidence=confidence,
        trend=trend,
        computed_at=now,
    )
    session.add(record)
    await session.flush()
    return record


async def get_forecast(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    domain: str,
) -> ForecastRecord:
    stmt = select(ForecastRecord).where(
        ForecastRecord.tenant_id == tenant_id,
        ForecastRecord.project_id == project_id,
        ForecastRecord.domain == domain,
    )
    record = await session.scalar(stmt)
    if record is None:
        raise ForecastNotFoundError(
            f"ForecastRecord for project={project_id} domain={domain} not found"
        )
    return record


async def list_forecasts(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[ForecastRecord]:
    stmt = select(ForecastRecord).where(
        ForecastRecord.tenant_id == tenant_id,
        ForecastRecord.project_id == project_id,
    )
    result = await session.execute(stmt)
    return list(result.scalars())
