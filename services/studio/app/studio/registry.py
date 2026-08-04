"""Builder registry for Green PM Studio — S18-01."""
from __future__ import annotations

from typing import Any

from app.studio.schemas import BUILDER_TYPES, BuilderConfig

_DEFAULT_CONFIGS: dict[str, dict] = {
    "WBS_TEMPLATE": {"levels": 4, "coding_scheme": "NUMERIC", "auto_rollup": True},
    "ACTIVITY_TEMPLATE": {"default_duration_days": 5, "buffer_pct": 10, "resource_loading": "FULL"},
    "EVIDENCE_SCORING": {
        "weights": {
            "credibility": 0.25,
            "specificity": 0.20,
            "recency": 0.20,
            "corroboration": 0.20,
            "relevance": 0.15,
        }
    },
    "VENDOR_SCORECARD": {
        "dimensions": ["DELIVERY", "QUALITY", "RESPONSIVENESS", "COMPLIANCE", "FINANCIAL"],
        "threshold_green": 0.75,
        "threshold_amber": 0.50,
    },
    "RISK_MATRIX": {
        "probability_bands": 5,
        "impact_bands": 5,
        "monte_carlo_iterations": 10000,
        "confidence_level": 0.80,
    },
    "DISPATCH_TEMPLATE": {
        "stages": 10,
        "readiness_threshold": 0.80,
        "auto_escalate_hours": 48,
    },
    "CHANGE_CATEGORY": {
        "categories": ["SCOPE", "SCHEDULE", "COST", "QUALITY", "RISK"],
        "approval_matrix": "TIERED",
        "min_impact_score": 0.10,
    },
    "READINESS_GATE": {
        "gates": 6,
        "blocking_required": True,
        "auto_pass_threshold": 0.95,
    },
    "SIMULATION_SCENARIO": {
        "perturbation_range_pct": 20,
        "projection_horizon_days": 90,
        "snapshot_on_create": True,
    },
    "COORDINATION_TEMPLATE": {
        "max_loop_iterations": 3,
        "close_within_hours": 72,
        "escalation_enabled": True,
    },
    "MEMORY_PATTERN": {
        "retention_days": 365,
        "similarity_threshold": 0.75,
        "max_patterns": 1000,
    },
    "FORECAST_MODEL": {
        "domains": 6,
        "horizon_weeks": 12,
        "confidence_interval": 0.80,
    },
    "ALIGNMENT_PROFILE": {
        "stakeholder_groups": ["EXEC", "PMO", "ENGINEERING", "VENDOR"],
        "gap_threshold": 0.20,
        "review_cadence_days": 14,
    },
    "DECISION_MATRIX": {
        "lifecycle_states": 10,
        "escalation_sla_hours": 48,
        "quorum_required": True,
    },
    "SYNC_POLICY": {
        "contradiction_window_hours": 24,
        "auto_resolve": False,
        "severity_levels": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    },
}

_REGISTRY: dict[str, BuilderConfig] = {
    bt: BuilderConfig(
        builder_type=bt,
        name=f"Default {bt.replace('_', ' ').title()}",
        config_data=_DEFAULT_CONFIGS[bt],
    )
    for bt in BUILDER_TYPES
}


def get_default_config(builder_type: str) -> BuilderConfig:
    if builder_type not in BUILDER_TYPES:
        raise ValueError(f"Unknown builder_type: '{builder_type}'")
    return _REGISTRY[builder_type]


def list_builder_types() -> list[str]:
    return sorted(BUILDER_TYPES)


def merge_config(builder_type: str, overrides: dict) -> dict:
    if builder_type not in BUILDER_TYPES:
        raise ValueError(f"Unknown builder_type: '{builder_type}'")
    base = dict(_DEFAULT_CONFIGS[builder_type])
    base.update(overrides)
    return base


def validate_config_keys(builder_type: str, config_data: dict) -> list[str]:
    """Return list of unknown keys not present in the default schema."""
    if builder_type not in BUILDER_TYPES:
        raise ValueError(f"Unknown builder_type: '{builder_type}'")
    known = set(_DEFAULT_CONFIGS[builder_type].keys())
    return [k for k in config_data if k not in known]


def apply_builder(builder_type: str, config_data: dict, target: Any) -> Any:
    """Apply builder config to a runtime target object (duck-typed)."""
    if builder_type not in BUILDER_TYPES:
        raise ValueError(f"Unknown builder_type: '{builder_type}'")
    merged = merge_config(builder_type, config_data)
    if hasattr(target, "apply_config"):
        target.apply_config(builder_type, merged)
    return target
