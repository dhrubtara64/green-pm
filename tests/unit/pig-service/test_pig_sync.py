"""PIG sync engine unit tests — S2-PIG-02."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

import sys, pathlib
# sync.py is in shared/, not pig-service — add repo root to path
_REPO = str(pathlib.Path(__file__).parents[3])
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from shared.pig.sync import (
    UntrackedEntityTypeError,
    _TRACKED_ENTITY_TYPES,
    build_activity_attributes,
    sync_entity,
)

TENANT_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
ENTITY_ID = uuid.uuid4()


# ── Tracked entity type guard ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_untracked_entity_type_raises():
    session = AsyncMock()
    with pytest.raises(UntrackedEntityTypeError, match="not tracked"):
        await sync_entity(
            session,
            tenant_id=TENANT_ID,
            project_id=PROJECT_ID,
            entity_type="invoice",
            entity_id=ENTITY_ID,
            attributes={},
        )


def test_all_22_entity_types_tracked():
    expected = {
        "activity", "milestone", "drawing", "document", "equipment",
        "vendor", "dispatch", "evidence", "change", "decision",
        "risk", "issue", "gate", "wbs", "package", "shipment",
        "claim", "payment", "inspection", "commissioning_item",
        "organizational_unit", "person",
    }
    assert _TRACKED_ENTITY_TYPES == expected


# ── Upsert behaviour ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_creates_new_node_when_absent():
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)  # no existing node
    session.add = MagicMock()
    session.flush = AsyncMock()

    result = await sync_entity(
        session,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        entity_type="activity",
        entity_id=ENTITY_ID,
        attributes={"name": "Pile driving"},
    )

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    assert result.entity_type == "activity"
    assert result.attributes["name"] == "Pile driving"
    assert result.tenant_id == TENANT_ID


@pytest.mark.asyncio
async def test_sync_updates_existing_node():
    existing = MagicMock()
    existing.attributes = {"name": "Old name"}
    existing.last_synced_at = None

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=existing)
    session.flush = AsyncMock()

    result = await sync_entity(
        session,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        entity_type="activity",
        entity_id=ENTITY_ID,
        attributes={"name": "New name", "progress_pct": 75},
    )

    assert result is existing
    assert existing.attributes == {"name": "New name", "progress_pct": 75}
    assert existing.last_synced_at is not None
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_last_synced_at_is_utc():
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock()

    result = await sync_entity(
        session,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        entity_type="risk",
        entity_id=ENTITY_ID,
        attributes={},
    )
    assert result.last_synced_at.tzinfo == timezone.utc


# ── build_activity_attributes ─────────────────────────────────────────────────

def test_build_activity_attributes_extracts_fields():
    activity = MagicMock()
    activity.name = "Cable pulling"
    activity.status = "in_progress"
    activity.progress_pct = 55
    activity.planned_start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    activity.planned_finish = datetime(2026, 10, 1, tzinfo=timezone.utc)
    activity.actual_start = None
    activity.actual_finish = None

    attrs = build_activity_attributes(activity)
    assert attrs["name"] == "Cable pulling"
    assert attrs["progress_pct"] == 55
    assert attrs["planned_start"] == "2026-09-01T00:00:00+00:00"
    assert attrs["actual_start"] is None


def test_build_activity_attributes_handles_missing_optional():
    activity = MagicMock(spec=["name"])
    activity.name = "Excavation"
    attrs = build_activity_attributes(activity)
    assert attrs["name"] == "Excavation"
    assert attrs["status"] is None
