"""Business logic for the Readiness Engine — S10-01–S10-05."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.readiness.gate_engine import compute_gate_status, identify_blocking_items
from app.readiness.model import ReadinessCriterion, ReadinessGate, ReadinessScore
from app.readiness.schemas import _CRITERIA_STATUSES, _GATE_TYPES

_GATE_STATUSES: frozenset[str] = frozenset(
    {"NOT_STARTED", "IN_PROGRESS", "READY", "BLOCKED"}
)


class GateNotFoundError(Exception):
    pass


class CriterionNotFoundError(Exception):
    pass


class InvalidGateTypeError(Exception):
    pass


class InvalidCriterionStatusError(Exception):
    pass


async def create_gate(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    gate_type: str,
) -> ReadinessGate:
    if gate_type not in _GATE_TYPES:
        raise InvalidGateTypeError(f"Unknown gate type: {gate_type!r}")
    gate = ReadinessGate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        gate_type=gate_type,
        status="NOT_STARTED",
        completion_percentage=0.0,
    )
    session.add(gate)
    await session.flush()
    return gate


async def get_gate(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    gate_id: uuid.UUID,
) -> ReadinessGate:
    gate = await session.scalar(
        select(ReadinessGate).where(
            ReadinessGate.id == gate_id,
            ReadinessGate.tenant_id == tenant_id,
        )
    )
    if gate is None:
        raise GateNotFoundError(f"Gate {gate_id} not found")
    return gate


async def list_gates(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[ReadinessGate]:
    rows = await session.execute(
        select(ReadinessGate).where(
            ReadinessGate.project_id == project_id,
            ReadinessGate.tenant_id == tenant_id,
        )
    )
    return list(rows.scalars())


async def create_criterion(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    gate_id: uuid.UUID,
    project_id: uuid.UUID,
    gate_type: str,
    title: str,
    description: Optional[str] = None,
    responsible_party: Optional[str] = None,
    due_date: Optional[date] = None,
) -> ReadinessCriterion:
    criterion = ReadinessCriterion(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        gate_id=gate_id,
        project_id=project_id,
        gate_type=gate_type,
        title=title,
        description=description,
        status="PENDING",
        responsible_party=responsible_party,
        due_date=due_date,
    )
    session.add(criterion)
    await session.flush()
    return criterion


async def update_criterion_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    criterion_id: uuid.UUID,
    status: str,
) -> ReadinessCriterion:
    if status not in _CRITERIA_STATUSES:
        raise InvalidCriterionStatusError(f"Unknown criterion status: {status!r}")
    criterion = await session.scalar(
        select(ReadinessCriterion).where(
            ReadinessCriterion.id == criterion_id,
            ReadinessCriterion.tenant_id == tenant_id,
        )
    )
    if criterion is None:
        raise CriterionNotFoundError(f"Criterion {criterion_id} not found")
    criterion.status = status
    await session.flush()
    return criterion


async def list_criteria(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    gate_id: uuid.UUID,
) -> list[ReadinessCriterion]:
    rows = await session.execute(
        select(ReadinessCriterion).where(
            ReadinessCriterion.gate_id == gate_id,
            ReadinessCriterion.tenant_id == tenant_id,
        )
    )
    return list(rows.scalars())


async def recompute_gate_score(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    gate_id: uuid.UUID,
    reference_date: Optional[date] = None,
) -> ReadinessScore:
    gate = await get_gate(session, tenant_id, gate_id)
    criteria = await list_criteria(session, tenant_id, gate_id)

    result = compute_gate_status(gate.gate_type, criteria, reference_date=reference_date)

    gate.status = result.status
    gate.completion_percentage = result.completion_percentage

    score = ReadinessScore(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        gate_id=gate_id,
        project_id=gate.project_id,
        gate_type=gate.gate_type,
        total_criteria=result.total_criteria,
        met_criteria=result.met_criteria,
        waived_criteria=result.waived_criteria,
        completion_percentage=result.completion_percentage,
    )
    session.add(score)
    await session.flush()
    return score


async def get_blocking_items(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    reference_date: Optional[date] = None,
) -> list[ReadinessCriterion]:
    rows = await session.execute(
        select(ReadinessCriterion).where(
            ReadinessCriterion.project_id == project_id,
            ReadinessCriterion.tenant_id == tenant_id,
            ReadinessCriterion.status == "PENDING",
        )
    )
    all_pending = list(rows.scalars())
    return identify_blocking_items(all_pending, reference_date=reference_date)
