"""Business logic for the Risk Engine — S9-01, S9-04, S9-05."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.monte_carlo.algorithm import run_monte_carlo
from app.monte_carlo.schemas import MonteCarloInput
from app.risk.model import Risk, RiskAssessment, RiskMitigation
from app.risk.schemas import RiskRegisterEntry, HeatMapCoordinates

_RISK_STATUSES: frozenset[str] = frozenset({"OPEN", "MITIGATING", "CLOSED"})
_MITIGATION_STATUSES: frozenset[str] = frozenset({"OPEN", "IN_PROGRESS", "CLOSED"})


class RiskNotFoundError(Exception):
    pass


class InvalidRiskStatusError(Exception):
    pass


class InvalidMitigationStatusError(Exception):
    pass


class ClosedMitigationError(Exception):
    pass


async def create_risk(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    category: str,
    description: str,
    probability: float,
    impact: float,
) -> Risk:
    risk = Risk(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        category=category,
        description=description,
        probability=probability,
        impact=impact,
        risk_score=round(probability * impact, 4),
        status="OPEN",
    )
    session.add(risk)
    await session.flush()
    return risk


async def get_risk(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    risk_id: uuid.UUID,
) -> Risk:
    risk = await session.scalar(
        select(Risk).where(Risk.id == risk_id, Risk.tenant_id == tenant_id)
    )
    if risk is None:
        raise RiskNotFoundError(f"Risk {risk_id} not found")
    return risk


async def list_risks(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    status: Optional[str] = None,
) -> list[Risk]:
    if status is not None and status not in _RISK_STATUSES:
        raise InvalidRiskStatusError(f"Unknown risk status: {status!r}")
    stmt = select(Risk).where(Risk.project_id == project_id, Risk.tenant_id == tenant_id)
    if status is not None:
        stmt = stmt.where(Risk.status == status)
    rows = await session.execute(stmt)
    return list(rows.scalars())


async def get_risk_register(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[RiskRegisterEntry]:
    rows = await session.execute(
        select(Risk)
        .where(Risk.project_id == project_id, Risk.tenant_id == tenant_id)
        .order_by(Risk.risk_score.desc())
    )
    risks = list(rows.scalars())
    return [
        RiskRegisterEntry(
            risk_id=r.id,
            category=r.category,
            description=r.description,
            risk_score=r.risk_score,
            heat_map=HeatMapCoordinates(x=r.probability, y=r.impact),
            status=r.status,
        )
        for r in risks
    ]


async def create_assessment(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    risk_id: uuid.UUID,
    project_id: uuid.UUID,
    notes: str,
    schedule_base: float,
    schedule_std_dev: float,
    cost_base: float,
    cost_std_dev: float,
    seed: Optional[int] = None,
) -> RiskAssessment:
    mc_input = MonteCarloInput(
        base_schedule=schedule_base,
        schedule_std_dev=schedule_std_dev,
        base_cost=cost_base,
        cost_std_dev=cost_std_dev,
    )
    mc_result = run_monte_carlo(mc_input, seed=seed)

    assessment = RiskAssessment(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        risk_id=risk_id,
        project_id=project_id,
        notes=notes,
        schedule_base=schedule_base,
        schedule_std_dev=schedule_std_dev,
        cost_base=cost_base,
        cost_std_dev=cost_std_dev,
        monte_carlo_result=mc_result.as_dict(),
    )
    session.add(assessment)
    await session.flush()
    return assessment


async def create_mitigation(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    risk_id: uuid.UUID,
    project_id: uuid.UUID,
    action: str,
    owner: str,
    due_date: Optional[date] = None,
) -> RiskMitigation:
    mitigation = RiskMitigation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        risk_id=risk_id,
        project_id=project_id,
        action=action,
        owner=owner,
        due_date=due_date,
        status="OPEN",
        effectiveness_score=0.0,
        outcome_verified=False,
    )
    session.add(mitigation)
    await session.flush()
    return mitigation


async def update_mitigation_effectiveness(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    mitigation_id: uuid.UUID,
    effectiveness_score: float,
    status: Optional[str] = None,
) -> RiskMitigation:
    if status is not None and status not in _MITIGATION_STATUSES:
        raise InvalidMitigationStatusError(f"Unknown mitigation status: {status!r}")

    mitigation = await session.scalar(
        select(RiskMitigation).where(
            RiskMitigation.id == mitigation_id,
            RiskMitigation.tenant_id == tenant_id,
        )
    )
    if mitigation is None:
        raise RiskNotFoundError(f"Mitigation {mitigation_id} not found")
    if mitigation.status == "CLOSED":
        raise ClosedMitigationError(
            f"Mitigation {mitigation_id} is CLOSED and cannot be modified"
        )

    mitigation.effectiveness_score = effectiveness_score
    mitigation.outcome_verified = True
    if status is not None:
        mitigation.status = status

    await session.flush()
    return mitigation
