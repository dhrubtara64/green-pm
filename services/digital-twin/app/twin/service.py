"""Executive Digital Twin + Command Centre service layer — S17-02, S17-03, S17-04."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.twin.model import CommandCentrePanel, EDTSynthesis
from app.twin.schemas import (
    COMMAND_CENTRE_PANELS,
    CommandCentrePanelCreate,
    EDTSynthesisCreate,
)


class EDTNotFoundError(Exception):
    pass


class CommandCentrePanelNotFoundError(Exception):
    pass


async def create_edt_synthesis(
    session,
    tenant_id: uuid.UUID,
    create: EDTSynthesisCreate,
) -> EDTSynthesis:
    """Persist one Monday EDT synthesis snapshot — S17-02."""
    record = EDTSynthesis(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=create.project_id,
        synthesis_date=create.synthesis_date,
        reality_panel=create.reality_panel,
        forecast_panel=create.forecast_panel,
        decisions_panel=create.decisions_panel,
        synthesized_at=datetime.now(timezone.utc),
    )
    session.add(record)
    await session.flush()
    return record


async def get_current_edt(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> EDTSynthesis:
    """Return the most-recent EDT synthesis for the project — S17-04."""
    stmt = (
        select(EDTSynthesis)
        .where(
            EDTSynthesis.tenant_id == tenant_id,
            EDTSynthesis.project_id == project_id,
        )
        .order_by(EDTSynthesis.synthesized_at.desc())
        .limit(1)
    )
    record = await session.scalar(stmt)
    if record is None:
        raise EDTNotFoundError(f"No EDT synthesis found for project {project_id}")
    return record


async def update_command_centre_panel(
    session,
    tenant_id: uuid.UUID,
    create: CommandCentrePanelCreate,
) -> CommandCentrePanel:
    """Upsert a Command Centre panel — creates or updates in place — S17-03.

    Production path writes to Firestore; this service layer handles the relational
    record for audit and API read access.
    """
    stmt = select(CommandCentrePanel).where(
        CommandCentrePanel.tenant_id == tenant_id,
        CommandCentrePanel.project_id == create.project_id,
        CommandCentrePanel.panel_name == create.panel_name,
    )
    existing = await session.scalar(stmt)
    now = datetime.now(timezone.utc)

    if existing is not None:
        existing.panel_data = create.panel_data
        existing.updated_at = now
        existing.triggered_by_event = create.triggered_by_event
        await session.flush()
        return existing

    record = CommandCentrePanel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=create.project_id,
        panel_name=create.panel_name,
        panel_data=create.panel_data,
        updated_at=now,
        triggered_by_event=create.triggered_by_event,
    )
    session.add(record)
    await session.flush()
    return record


async def get_command_centre_panel(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    panel_name: str,
) -> CommandCentrePanel:
    stmt = select(CommandCentrePanel).where(
        CommandCentrePanel.tenant_id == tenant_id,
        CommandCentrePanel.project_id == project_id,
        CommandCentrePanel.panel_name == panel_name,
    )
    record = await session.scalar(stmt)
    if record is None:
        raise CommandCentrePanelNotFoundError(
            f"Panel {panel_name!r} not found for project {project_id}"
        )
    return record


async def list_command_centre_panels(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[CommandCentrePanel]:
    stmt = select(CommandCentrePanel).where(
        CommandCentrePanel.tenant_id == tenant_id,
        CommandCentrePanel.project_id == project_id,
    )
    result = await session.execute(stmt)
    return list(result.scalars())
