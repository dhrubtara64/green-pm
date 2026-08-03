"""Supply chain service — dispatch CRUD and stage transitions."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select

from app.dispatch.model import Dispatch, MaterialItem, PurchaseOrder, Vendor, MaterialPackage
from app.dispatch.schemas import _DISPATCH_STAGES
from app.dispatch.state_machine import DispatchStateMachine
from app.materials.service import compute_readiness_score

_state_machine = DispatchStateMachine()


class DispatchNotFoundError(Exception):
    pass


async def create_dispatch(session, tenant_id: uuid.UUID, po_id: uuid.UUID,
                          project_id: uuid.UUID, dispatch_number: str) -> Dispatch:
    dispatch = Dispatch(
        id=uuid.uuid4(),
        po_id=po_id,
        project_id=project_id,
        tenant_id=tenant_id,
        dispatch_number=dispatch_number,
        current_stage=_DISPATCH_STAGES[0],
        material_readiness_score=compute_readiness_score(_DISPATCH_STAGES[0]),
        critical_material_count=0,
    )
    session.add(dispatch)
    await session.flush()
    return dispatch


async def get_dispatch(session, tenant_id: uuid.UUID, dispatch_id: uuid.UUID) -> Dispatch:
    result = await session.scalar(
        select(Dispatch).where(
            and_(
                Dispatch.id == dispatch_id,
                Dispatch.tenant_id == tenant_id,
            )
        )
    )
    if result is None:
        raise DispatchNotFoundError(f"Dispatch {dispatch_id} not found")
    return result


async def list_dispatches(session, tenant_id: uuid.UUID, project_id: uuid.UUID) -> list[Dispatch]:
    result = await session.execute(
        select(Dispatch).where(
            and_(
                Dispatch.project_id == project_id,
                Dispatch.tenant_id == tenant_id,
            )
        )
    )
    return list(result.scalars().all())


async def transition_dispatch_stage(
    session,
    tenant_id: uuid.UUID,
    dispatch_id: uuid.UUID,
    target_stage: str,
) -> Dispatch:
    dispatch = await get_dispatch(session, tenant_id, dispatch_id)
    _state_machine.validate_transition(dispatch.current_stage, target_stage)
    dispatch.current_stage = target_stage
    dispatch.material_readiness_score = compute_readiness_score(target_stage)
    await session.flush()
    return dispatch


async def count_critical_materials(
    session, tenant_id: uuid.UUID, dispatch_id: uuid.UUID
) -> int:
    """Count material items flagged is_critical for a dispatch (via packages)."""
    result = await session.execute(
        select(MaterialItem).join(
            MaterialPackage, MaterialItem.package_id == MaterialPackage.id
        ).where(
            and_(
                MaterialPackage.dispatch_id == dispatch_id,
                MaterialItem.tenant_id == tenant_id,
                MaterialItem.is_critical.is_(True),
            )
        )
    )
    return len(list(result.scalars().all()))
