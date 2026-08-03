"""Audit logger unit tests — S1-CORE-04.

Tests input validation and object construction without a database.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

from app.audit.logger import log_audit_event

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
ENTITY_ID = uuid.uuid4()


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_valid_create_event():
    session = _mock_session()
    entry = await log_audit_event(
        session,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        action="CREATE",
        entity_type="project",
        entity_id=ENTITY_ID,
        new_value={"name": "Bridge"},
    )
    assert entry.action == "CREATE"
    assert entry.entity_type == "project"
    assert entry.entity_id == ENTITY_ID
    assert entry.tenant_id == TENANT_ID
    assert entry.new_value == {"name": "Bridge"}
    assert entry.old_value is None
    session.add.assert_called_once_with(entry)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_valid_update_event_with_old_and_new():
    session = _mock_session()
    entry = await log_audit_event(
        session,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        action="UPDATE",
        entity_type="user",
        old_value={"role": "viewer"},
        new_value={"role": "engineer"},
    )
    assert entry.action == "UPDATE"
    assert entry.old_value == {"role": "viewer"}
    assert entry.new_value == {"role": "engineer"}


@pytest.mark.asyncio
async def test_invalid_action_raises_value_error():
    session = _mock_session()
    with pytest.raises(ValueError, match="Invalid audit action"):
        await log_audit_event(
            session,
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action="HACK",
            entity_type="tenant",
        )


@pytest.mark.asyncio
async def test_all_valid_actions_accepted():
    for action in ["CREATE", "UPDATE", "DELETE", "VIEW"]:
        session = _mock_session()
        entry = await log_audit_event(
            session,
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=action,
            entity_type="project",
        )
        assert entry.action == action


@pytest.mark.asyncio
async def test_user_id_optional():
    session = _mock_session()
    entry = await log_audit_event(
        session,
        tenant_id=TENANT_ID,
        user_id=None,
        action="CREATE",
        entity_type="tenant",
    )
    assert entry.user_id is None


@pytest.mark.asyncio
async def test_each_entry_gets_unique_id():
    s1, s2 = _mock_session(), _mock_session()
    e1 = await log_audit_event(s1, tenant_id=TENANT_ID, user_id=USER_ID, action="VIEW", entity_type="x")
    e2 = await log_audit_event(s2, tenant_id=TENANT_ID, user_id=USER_ID, action="VIEW", entity_type="x")
    assert e1.id != e2.id
