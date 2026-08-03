"""PIG Query Service schema unit tests — S2-PIG-01."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from app.graph.schemas import EdgeCreate, NodeCreate, NodeUpdate, NodeResponse


TENANT_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
NODE_ID = uuid.uuid4()
ENTITY_ID = uuid.uuid4()


# ── NodeCreate ────────────────────────────────────────────────────────────────

def test_node_create_valid():
    n = NodeCreate(project_id=PROJECT_ID, entity_type="activity", entity_id=ENTITY_ID)
    assert n.entity_type == "activity"
    assert n.attributes == {}


@pytest.mark.parametrize("entity_type", [
    "activity", "milestone", "drawing", "document", "equipment",
    "vendor", "dispatch", "evidence", "change", "decision",
    "risk", "issue", "gate", "wbs", "package", "shipment",
    "claim", "payment", "inspection", "commissioning_item",
    "organizational_unit", "person",
])
def test_all_22_entity_types_accepted(entity_type):
    n = NodeCreate(project_id=PROJECT_ID, entity_type=entity_type, entity_id=ENTITY_ID)
    assert n.entity_type == entity_type


def test_unknown_entity_type_rejected():
    with pytest.raises(ValidationError, match="Unknown entity_type"):
        NodeCreate(project_id=PROJECT_ID, entity_type="spaceship", entity_id=ENTITY_ID)


def test_node_create_attributes_stored():
    n = NodeCreate(
        project_id=PROJECT_ID,
        entity_type="activity",
        entity_id=ENTITY_ID,
        attributes={"name": "Bridge excavation", "progress": 42},
    )
    assert n.attributes["progress"] == 42


# ── NodeUpdate ────────────────────────────────────────────────────────────────

def test_node_update_requires_attributes():
    u = NodeUpdate(attributes={"status": "delayed"})
    assert u.attributes["status"] == "delayed"


# ── EdgeCreate ────────────────────────────────────────────────────────────────

def test_edge_create_valid():
    e = EdgeCreate(
        project_id=PROJECT_ID,
        source_node_id=uuid.uuid4(),
        target_node_id=uuid.uuid4(),
        edge_type="DEPENDS_ON",
    )
    assert e.weight == 1.0
    assert e.expires_at is None


@pytest.mark.parametrize("edge_type", [
    "BLOCKS", "SUPPLIES_TO", "APPROVED_BY", "IMPACTS", "DEPENDS_ON",
    "SUPERSEDES", "CONFLICTS_WITH", "DELIVERS_FOR", "REVIEWS", "ASSIGNED_TO",
    "COORDINATES_WITH", "ESCALATES_TO", "PRECEDED_BY", "PARALLEL_WITH",
    "REQUIRES", "SATISFIES", "VERIFIES", "CLOSES", "MONITORS", "TRIGGERS",
    "OWNS", "RAISED_BY", "RESOLVED_BY", "REFERENCES", "SUPERSEDED_BY",
    "MITIGATES", "RAISES_RISK_TO", "CLEARS", "GATES", "REPORTS_TO",
])
def test_all_30_edge_types_accepted(edge_type):
    e = EdgeCreate(
        project_id=PROJECT_ID,
        source_node_id=uuid.uuid4(),
        target_node_id=uuid.uuid4(),
        edge_type=edge_type,
    )
    assert e.edge_type == edge_type


def test_unknown_edge_type_rejected():
    with pytest.raises(ValidationError, match="Unknown edge_type"):
        EdgeCreate(
            project_id=PROJECT_ID,
            source_node_id=uuid.uuid4(),
            target_node_id=uuid.uuid4(),
            edge_type="DESTROYS",
        )


def test_edge_weight_out_of_range_rejected():
    with pytest.raises(ValidationError):
        EdgeCreate(
            project_id=PROJECT_ID,
            source_node_id=uuid.uuid4(),
            target_node_id=uuid.uuid4(),
            edge_type="BLOCKS",
            weight=1.5,
        )


def test_edge_weight_zero_accepted():
    e = EdgeCreate(
        project_id=PROJECT_ID,
        source_node_id=uuid.uuid4(),
        target_node_id=uuid.uuid4(),
        edge_type="BLOCKS",
        weight=0.0,
    )
    assert e.weight == 0.0


# ── NodeResponse from_attributes ──────────────────────────────────────────────

def test_node_response_from_orm():
    class FakeNode:
        id = NODE_ID
        project_id = PROJECT_ID
        tenant_id = TENANT_ID
        entity_type = "activity"
        entity_id = ENTITY_ID
        attributes = {"name": "X"}
        last_synced_at = datetime.now(timezone.utc)

    r = NodeResponse.model_validate(FakeNode())
    assert r.entity_type == "activity"
    assert r.attributes == {"name": "X"}
