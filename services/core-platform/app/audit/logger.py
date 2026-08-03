from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.audit import AuditLog

_VALID_ACTIONS = frozenset({"CREATE", "UPDATE", "DELETE", "VIEW"})


async def log_audit_event(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    action: str,
    entity_type: str,
    entity_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    old_value: Optional[dict[str, Any]] = None,
    new_value: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    if action not in _VALID_ACTIONS:
        raise ValueError(f"Invalid audit action: {action!r}. Must be one of {_VALID_ACTIONS}")

    entry = AuditLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
    )
    session.add(entry)
    await session.flush()
    return entry
