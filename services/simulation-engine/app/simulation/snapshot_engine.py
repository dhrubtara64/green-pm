"""PIG snapshot capture — S11-02."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PigNodeLike(Protocol):
    node_ref: str
    duration_days: float
    cost_estimate: float


def capture_pig_snapshot(nodes: list) -> dict:
    """Serialise PIG-like node objects into a JSONB-storable snapshot dict.

    Works with ORM rows, MagicMocks, or any duck-typed object.
    Missing attributes default to 0.0.  None values are coerced to 0.0.
    """
    return {
        "nodes": [
            {
                "node_ref": n.node_ref,
                "duration_days": float(getattr(n, "duration_days", 0.0) or 0.0),
                "cost_estimate": float(getattr(n, "cost_estimate", 0.0) or 0.0),
                "completion_pct": float(getattr(n, "completion_pct", 0.0) or 0.0),
            }
            for n in nodes
        ]
    }
