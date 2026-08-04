"""Event-to-coordination-item generation — S12-02."""
from __future__ import annotations
import uuid
from app.coordination.schemas import CoordinationItemCreate

_SUBSCRIBED_EVENTS: frozenset[str] = frozenset({
    "RiskIdentified",
    "RiskEscalated",
    "ReadinessGateUpdated",
    "SupplyChainDelayDetected",
    "VendorPerformanceFlagged",
    "ImpactAssessmentCompleted",
    "CriticalPathChanged",
    "SimulationProjectionCompleted",
})

_EVENT_TITLES: dict[str, str] = {
    "RiskIdentified": "Risk identified — coordination required",
    "RiskEscalated": "Risk escalated — immediate coordination required",
    "ReadinessGateUpdated": "Gate readiness change — review required",
    "SupplyChainDelayDetected": "Supply chain delay — coordination action needed",
    "VendorPerformanceFlagged": "Vendor performance flag — corrective action required",
    "ImpactAssessmentCompleted": "Impact assessment complete — assign action owner",
    "CriticalPathChanged": "Critical path change detected — schedule coordination required",
    "SimulationProjectionCompleted": "Simulation projection complete — decision required",
}


def generate_coordination_items(
    event: dict,
    project_id: uuid.UUID,
) -> list[CoordinationItemCreate]:
    """Generate coordination items from an engine event.

    Returns an empty list for unknown or non-significant events.
    Each significant event produces exactly one coordination item.
    The source_event_id is set to deduplicate on re-delivery.
    """
    event_type = event.get("event_type", "")
    if event_type not in _SUBSCRIBED_EVENTS:
        return []
    source_event_id = event.get("event_id", "")
    title = _EVENT_TITLES.get(event_type, f"Coordination required: {event_type}")
    return [
        CoordinationItemCreate(
            project_id=project_id,
            title=title,
            source_event_id=source_event_id,
        )
    ]


def is_duplicate_event(existing_source_ids: set[str], source_event_id: str) -> bool:
    """Return True if a coordination item already exists for this source_event_id."""
    return bool(source_event_id) and source_event_id in existing_source_ids
