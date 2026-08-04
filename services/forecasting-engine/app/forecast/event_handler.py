"""Forecasting Engine event handler — S14-02."""
from typing import Optional

_SUBSCRIBED_EVENTS: frozenset[str] = frozenset({
    "CriticalPathChanged",
    "SimulationCompleted",
    "RiskIdentified",
    "RiskResolved",
    "RiskMitigated",
    "ReadinessGateBlocked",
    "ReadinessGateCleared",
    "VendorScoreComputed",
    "VendorDelayFlagged",
    "SupplyChainDisrupted",
    "SupplyChainOrderDispatched",
    "EvidenceReviewed",
    "EvidenceUploaded",
    "ImpactAssessed",
    "ChangeInitiated",
    "CoordinationItemCreated",
    "DecisionApproved",
})

_EVENT_DOMAINS: dict[str, frozenset[str]] = {
    "CriticalPathChanged":       frozenset({"SCHEDULE", "RESOURCE"}),
    "SimulationCompleted":       frozenset({"SCHEDULE", "BUDGET", "CASH_FLOW", "COMMISSIONING"}),
    "RiskIdentified":            frozenset({"SCHEDULE", "BUDGET", "QUALITY"}),
    "RiskResolved":              frozenset({"SCHEDULE", "BUDGET"}),
    "RiskMitigated":             frozenset({"SCHEDULE", "BUDGET"}),
    "ReadinessGateBlocked":      frozenset({"COMMISSIONING", "QUALITY", "SCHEDULE"}),
    "ReadinessGateCleared":      frozenset({"COMMISSIONING", "QUALITY"}),
    "VendorScoreComputed":       frozenset({"BUDGET", "QUALITY", "CASH_FLOW"}),
    "VendorDelayFlagged":        frozenset({"SCHEDULE", "BUDGET", "CASH_FLOW"}),
    "SupplyChainDisrupted":      frozenset({"BUDGET", "RESOURCE", "CASH_FLOW"}),
    "SupplyChainOrderDispatched": frozenset({"RESOURCE", "CASH_FLOW"}),
    "EvidenceReviewed":          frozenset({"QUALITY"}),
    "EvidenceUploaded":          frozenset({"QUALITY"}),
    "ImpactAssessed":            frozenset({"SCHEDULE", "BUDGET", "RESOURCE"}),
    "ChangeInitiated":           frozenset({"SCHEDULE", "RESOURCE"}),
    "CoordinationItemCreated":   frozenset({"RESOURCE", "SCHEDULE"}),
    "DecisionApproved":          frozenset({"SCHEDULE", "BUDGET", "RESOURCE"}),
}

_NEGATIVE_TREND_PAIRS: frozenset[tuple] = frozenset({
    ("RiskIdentified", "SCHEDULE"),
    ("RiskIdentified", "BUDGET"),
    ("RiskIdentified", "QUALITY"),
    ("VendorDelayFlagged", "SCHEDULE"),
    ("VendorDelayFlagged", "BUDGET"),
    ("VendorDelayFlagged", "CASH_FLOW"),
    ("SupplyChainDisrupted", "BUDGET"),
    ("SupplyChainDisrupted", "RESOURCE"),
    ("SupplyChainDisrupted", "CASH_FLOW"),
    ("ReadinessGateBlocked", "COMMISSIONING"),
    ("ReadinessGateBlocked", "QUALITY"),
    ("ReadinessGateBlocked", "SCHEDULE"),
})

_POSITIVE_TREND_PAIRS: frozenset[tuple] = frozenset({
    ("RiskResolved", "SCHEDULE"),
    ("RiskResolved", "BUDGET"),
    ("RiskMitigated", "SCHEDULE"),
    ("RiskMitigated", "BUDGET"),
    ("ReadinessGateCleared", "COMMISSIONING"),
    ("ReadinessGateCleared", "QUALITY"),
    ("VendorScoreComputed", "QUALITY"),
    ("VendorScoreComputed", "BUDGET"),
    ("DecisionApproved", "SCHEDULE"),
    ("DecisionApproved", "BUDGET"),
    ("DecisionApproved", "RESOURCE"),
})


def get_affected_domains(event_type: str) -> frozenset[str]:
    """Returns the set of forecast domains affected by this event type."""
    return _EVENT_DOMAINS.get(event_type, frozenset())


def _infer_trend(event_type: str, domain: str) -> str:
    if (event_type, domain) in _NEGATIVE_TREND_PAIRS:
        return "DOWN"
    if (event_type, domain) in _POSITIVE_TREND_PAIRS:
        return "UP"
    return "STABLE"


def extract_domain_forecast(event: dict, domain: str) -> Optional[dict]:
    """Extract forecast parameters for a specific domain from an event.

    Returns None if event_type is not subscribed or does not affect the domain.
    Otherwise returns {current_value, forecast_value, confidence, trend}.
    """
    event_type = event.get("event_type", "")
    if not event_type or event_type not in _SUBSCRIBED_EVENTS:
        return None
    if domain not in get_affected_domains(event_type):
        return None
    confidence = float(event.get("confidence_score", 0.7))
    confidence = min(1.0, max(0.0, confidence))
    current_value = float(event.get("current_value", 0.0))
    forecast_value = float(event.get("forecast_value", current_value))
    trend = _infer_trend(event_type, domain)
    return {
        "current_value": current_value,
        "forecast_value": forecast_value,
        "confidence": confidence,
        "trend": trend,
    }
