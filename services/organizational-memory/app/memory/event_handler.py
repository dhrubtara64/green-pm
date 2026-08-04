"""Event-to-memory-record generation — S13-02, S13-03, S13-04."""
from __future__ import annotations
import uuid
from typing import Optional

from app.memory.schemas import MemoryRecordCreate, _MEMORY_CATEGORIES

_SUBSCRIBED_EVENTS: frozenset[str] = frozenset({
    "DecisionApproved",
    "VendorScoreComputed",
    "RiskResolved",
    "RiskMitigated",
})

_EVENT_CATEGORY: dict[str, str] = {
    "DecisionApproved": "DECISION",
    "VendorScoreComputed": "VENDOR",
    "RiskResolved": "RISK",
    "RiskMitigated": "RISK",
}

_EVENT_SUMMARIES: dict[str, str] = {
    "DecisionApproved": "Decision approved — outcome recorded for institutional learning",
    "VendorScoreComputed": "Vendor score computed — trajectory pattern recorded",
    "RiskResolved": "Risk resolved — recovery strategy recorded",
    "RiskMitigated": "Risk mitigated — mitigation effectiveness recorded",
}


def extract_memory_record_from_event(
    event: dict,
    project_id: uuid.UUID,
) -> Optional[MemoryRecordCreate]:
    """Return MemoryRecordCreate for known events, None for unknown/empty events."""
    event_type = event.get("event_type", "")
    if not event_type or event_type not in _SUBSCRIBED_EVENTS:
        return None

    category = _EVENT_CATEGORY[event_type]
    summary = _EVENT_SUMMARIES[event_type]

    entity_id_raw = event.get("entity_id")
    entity_id: Optional[uuid.UUID] = None
    if entity_id_raw:
        try:
            entity_id = uuid.UUID(str(entity_id_raw))
        except (ValueError, AttributeError):
            entity_id = None

    entity_type: Optional[str] = event.get("entity_type")

    context: Optional[dict] = event.get("context")
    if not isinstance(context, dict):
        context = None

    confidence_score = float(event.get("confidence_score", 0.7))
    confidence_score = max(0.0, min(1.0, confidence_score))

    outcome: Optional[str] = event.get("outcome")

    return MemoryRecordCreate(
        project_id=project_id,
        category=category,
        summary=summary,
        entity_id=entity_id,
        entity_type=entity_type,
        context=context,
        confidence_score=confidence_score,
        outcome=outcome,
    )


def extract_pattern_data_from_event(event: dict) -> Optional[dict]:
    """Extract trigger_conditions and outcome for upsert_pattern from an event.

    Returns dict with keys: pattern_name, trigger_conditions, outcome, confidence_score.
    Returns None for unknown events.
    """
    event_type = event.get("event_type", "")
    if not event_type or event_type not in _SUBSCRIBED_EVENTS:
        return None

    category = _EVENT_CATEGORY[event_type]
    context = event.get("context") or {}
    outcome = event.get("outcome", "")
    confidence_score = float(event.get("confidence_score", 0.7))
    confidence_score = max(0.0, min(1.0, confidence_score))

    pattern_name = f"{event_type}:{category}"
    if context.get("pattern_name"):
        pattern_name = str(context["pattern_name"])

    return {
        "pattern_name": pattern_name,
        "category": category,
        "trigger_conditions": {k: v for k, v in context.items() if k != "pattern_name"},
        "outcome": outcome,
        "confidence_score": confidence_score,
    }
