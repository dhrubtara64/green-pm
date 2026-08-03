"""EventEnvelope invariant tests — written before implementation (TDD).

These tests encode the invariants defined in Engineering Standards § 4.
Every invariant must pass before any engine may publish events.
"""
from __future__ import annotations

import uuid
from datetime import timezone

import pytest
from pydantic import ValidationError

from shared.events.envelope import EventEnvelope

pytestmark = pytest.mark.unit

TENANT_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()


# ── Invariant 1: Valid envelope is created successfully ───────────────────────

def test_valid_envelope_creation():
    env = EventEnvelope(
        event_type="ActivityDelayed",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        payload={"activity_id": str(uuid.uuid4()), "delay_days": 3},
    )
    assert env.event_type == "ActivityDelayed"
    assert env.tenant_id == TENANT_ID
    assert env.schema_version == "1.0.0"
    assert env.event_id is not None
    assert env.correlation_id is not None


# ── Invariant 2: schema_version must be SemVer ────────────────────────────────

@pytest.mark.parametrize("bad_version", [
    "1.0",        # missing patch
    "v1.0.0",     # 'v' prefix not allowed
    "1.0.0.0",    # four parts
    "latest",     # non-numeric
    "",           # empty
])
def test_invalid_schema_version_rejected(bad_version):
    with pytest.raises(ValidationError, match="schema_version"):
        EventEnvelope(
            event_type="ActivityDelayed",
            tenant_id=TENANT_ID,
            schema_version=bad_version,
        )


def test_valid_schema_versions_accepted():
    for version in ["1.0.0", "2.14.3", "0.0.1", "10.100.1000"]:
        env = EventEnvelope(
            event_type="ActivityDelayed",
            tenant_id=TENANT_ID,
            schema_version=version,
        )
        assert env.schema_version == version


# ── Invariant 3: event_type must be PascalCase ───────────────────────────────

@pytest.mark.parametrize("bad_type", [
    "activityDelayed",   # camelCase — not allowed
    "activity_delayed",  # snake_case — not allowed
    "ACTIVITY_DELAYED",  # SCREAMING_SNAKE — not allowed
    "",                  # empty
    " ActivityDelayed",  # leading space
])
def test_invalid_event_type_rejected(bad_type):
    with pytest.raises(ValidationError, match="event_type"):
        EventEnvelope(event_type=bad_type, tenant_id=TENANT_ID)


def test_valid_event_types_accepted():
    for event_type in [
        "ActivityDelayed", "DrawingRevisionIssued", "EvidenceScoreComputed",
        "CoordinationItemClosed", "VendorScoreUpdated",
    ]:
        env = EventEnvelope(event_type=event_type, tenant_id=TENANT_ID)
        assert env.event_type == event_type


# ── Invariant 4: event_id and correlation_id are always UUID ─────────────────

def test_event_id_is_uuid():
    env = EventEnvelope(event_type="ActivityDelayed", tenant_id=TENANT_ID)
    assert isinstance(env.event_id, uuid.UUID)


def test_correlation_id_auto_generated():
    env = EventEnvelope(event_type="ActivityDelayed", tenant_id=TENANT_ID)
    assert isinstance(env.correlation_id, uuid.UUID)


def test_two_envelopes_have_different_event_ids():
    env1 = EventEnvelope(event_type="ActivityDelayed", tenant_id=TENANT_ID)
    env2 = EventEnvelope(event_type="ActivityDelayed", tenant_id=TENANT_ID)
    assert env1.event_id != env2.event_id


# ── Invariant 5: occurred_at is always UTC ────────────────────────────────────

def test_occurred_at_is_utc():
    env = EventEnvelope(event_type="ActivityDelayed", tenant_id=TENANT_ID)
    assert env.occurred_at.tzinfo == timezone.utc


# ── Invariant 6: EventEnvelope is immutable after creation ───────────────────

def test_envelope_is_frozen():
    env = EventEnvelope(event_type="ActivityDelayed", tenant_id=TENANT_ID)
    with pytest.raises(Exception):  # ValidationError or TypeError depending on Pydantic
        env.event_type = "SomethingElse"  # type: ignore[misc]


# ── Invariant 7: causation_id propagates event chains ────────────────────────

def test_causation_id_can_be_set():
    parent_id = uuid.uuid4()
    env = EventEnvelope(
        event_type="RiskScoreUpdated",
        tenant_id=TENANT_ID,
        causation_id=parent_id,
    )
    assert env.causation_id == parent_id


def test_causation_id_is_none_by_default():
    env = EventEnvelope(event_type="ActivityDelayed", tenant_id=TENANT_ID)
    assert env.causation_id is None


# ── Invariant 8: correlation_id can be inherited from parent ─────────────────

def test_correlation_id_can_be_provided():
    chain_id = uuid.uuid4()
    env = EventEnvelope(
        event_type="CriticalPathChanged",
        tenant_id=TENANT_ID,
        correlation_id=chain_id,
    )
    assert env.correlation_id == chain_id


# ── Invariant 9: payload is always a dict ────────────────────────────────────

def test_payload_defaults_to_empty_dict():
    env = EventEnvelope(event_type="ActivityDelayed", tenant_id=TENANT_ID)
    assert env.payload == {}


def test_payload_accepts_nested_data():
    payload = {
        "activity_id": str(uuid.uuid4()),
        "delay_days": 5,
        "impacts": ["cost", "schedule"],
        "metadata": {"source": "scheduler"},
    }
    env = EventEnvelope(
        event_type="ActivityDelayed",
        tenant_id=TENANT_ID,
        payload=payload,
    )
    assert env.payload == payload


# ── Invariant 10: project_id is optional ─────────────────────────────────────

def test_project_id_is_optional():
    env = EventEnvelope(event_type="TenantCreated", tenant_id=TENANT_ID)
    assert env.project_id is None


def test_project_id_can_be_set():
    env = EventEnvelope(
        event_type="ActivityDelayed",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
    )
    assert env.project_id == PROJECT_ID
