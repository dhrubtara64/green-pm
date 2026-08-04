"""Decision Engine service layer — S15-02, S15-03, S15-04, S15-05."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.decision.lifecycle import (
    is_valid_transition,
    required_approval_count,
    requires_approval_gate,
)
from app.decision.model import Decision, DecisionApproval, DecisionOption
from app.decision.schemas import DecisionApprovalCreate, DecisionCreate, DecisionOptionCreate


class DecisionNotFoundError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


class InsufficientApprovalsError(Exception):
    pass


async def create_decision(
    session,
    tenant_id: uuid.UUID,
    create: DecisionCreate,
    historical_context: Optional[list] = None,
) -> Decision:
    record = Decision(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=create.project_id,
        title=create.title,
        description=create.description,
        lifecycle_status="DRAFT",
        priority=create.priority,
        impact_level=create.impact_level,
        approval_required=create.approval_required,
        approval_count=0,
        historical_context=historical_context,
        created_at=datetime.now(timezone.utc),
    )
    session.add(record)
    await session.flush()
    return record


async def advance_decision_state(
    session,
    tenant_id: uuid.UUID,
    decision_id: uuid.UUID,
    to_state: str,
) -> Decision:
    stmt = select(Decision).where(
        Decision.tenant_id == tenant_id,
        Decision.id == decision_id,
    )
    decision = await session.scalar(stmt)
    if decision is None:
        raise DecisionNotFoundError(f"Decision {decision_id} not found")
    if not is_valid_transition(decision.lifecycle_status, to_state):
        raise InvalidTransitionError(
            f"Cannot transition from {decision.lifecycle_status!r} to {to_state!r}"
        )
    if requires_approval_gate(to_state):
        needed = required_approval_count(decision.impact_level, decision.approval_required)
        if decision.approval_count < needed:
            raise InsufficientApprovalsError(
                f"Requires {needed} approvals, got {decision.approval_count}"
            )
    decision.lifecycle_status = to_state
    await session.flush()
    return decision


async def submit_approval(
    session,
    tenant_id: uuid.UUID,
    create: DecisionApprovalCreate,
) -> Decision:
    stmt = select(Decision).where(
        Decision.tenant_id == tenant_id,
        Decision.id == create.decision_id,
    )
    decision = await session.scalar(stmt)
    if decision is None:
        raise DecisionNotFoundError(f"Decision {create.decision_id} not found")
    approval = DecisionApproval(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        decision_id=create.decision_id,
        approver_id=create.approver_id,
        approved=create.approved,
        comment=create.comment,
        created_at=datetime.now(timezone.utc),
    )
    session.add(approval)
    if create.approved:
        decision.approval_count += 1
    await session.flush()
    return decision


async def add_option(
    session,
    tenant_id: uuid.UUID,
    create: DecisionOptionCreate,
) -> DecisionOption:
    option = DecisionOption(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        decision_id=create.decision_id,
        option_text=create.option_text,
        pros=create.pros,
        cons=create.cons,
        is_selected=False,
    )
    session.add(option)
    await session.flush()
    return option


async def list_decisions(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    lifecycle_status: Optional[str] = None,
) -> list[Decision]:
    stmt = select(Decision).where(
        Decision.tenant_id == tenant_id,
        Decision.project_id == project_id,
    )
    if lifecycle_status is not None:
        stmt = stmt.where(Decision.lifecycle_status == lifecycle_status)
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_decision(
    session,
    tenant_id: uuid.UUID,
    decision_id: uuid.UUID,
) -> Decision:
    stmt = select(Decision).where(
        Decision.tenant_id == tenant_id,
        Decision.id == decision_id,
    )
    record = await session.scalar(stmt)
    if record is None:
        raise DecisionNotFoundError(f"Decision {decision_id} not found")
    return record
