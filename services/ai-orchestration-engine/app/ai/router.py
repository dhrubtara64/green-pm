"""NL query → engine routing for AI Orchestration Engine — S16-02.

Engine names are never surfaced in API responses; routing is purely internal.
"""
from __future__ import annotations

# Keywords that trigger routing to each engine — ordered specific to general
_ENGINE_KEYWORDS: dict[str, frozenset[str]] = {
    "risk-engine": frozenset({
        "risk", "threat", "hazard", "danger", "probability", "likelihood", "monte carlo",
    }),
    "impact-engine": frozenset({
        "impact", "cascade", "consequence", "effect", "ripple", "downstream",
    }),
    "dependency-engine": frozenset({
        "dependency", "dependencies", "critical path", "float", "chain", "deadline", "cpm",
    }),
    "supply-chain-engine": frozenset({
        "supply", "material", "delivery", "dispatch", "procurement", "logistics",
    }),
    "vendor-engine": frozenset({
        "vendor", "supplier", "contractor", "scorecard", "subcontractor",
    }),
    "readiness-engine": frozenset({
        "ready", "readiness", "gate", "go-live", "launch", "checklist", "criteria",
    }),
    "simulation-engine": frozenset({
        "simulation", "scenario", "what-if", "what if", "perturbation", "projection",
    }),
    "coordination-engine": frozenset({
        "coordination", "action", "close loop", "pipeline", "closed",
    }),
    "organizational-memory": frozenset({
        "memory", "institutional", "lesson", "pattern", "learned", "historical",
    }),
    "forecasting-engine": frozenset({
        "forecast", "prediction", "trend", "estimate", "timeline", "schedule", "outlook",
    }),
    "alignment-engine": frozenset({
        "alignment", "stakeholder", "gap", "communication", "awareness", "informed",
    }),
    "decision-engine": frozenset({
        "decision", "approve", "approval", "pending", "lifecycle", "deferred",
    }),
    "sync-engine": frozenset({
        "inconsistency", "contradiction", "sync", "conflict", "weight", "diverge",
    }),
    "evidence-engine": frozenset({
        "evidence", "document", "proof", "record", "score", "artefact", "upload",
    }),
    "pig-service": frozenset({
        "pig", "graph", "node", "edge", "relationship", "traverse",
    }),
    "core-platform": frozenset({
        "project", "workspace", "tenant", "user", "general", "overview",
    }),
}

_FALLBACK_ENGINE: str = "core-platform"


def route_query(query_text: str, max_engines: int = 5) -> list[str]:
    """Return engine names that match the NL query — internal routing only, never surfaced.

    Matches by keyword overlap; ties broken by dictionary order. Falls back to
    core-platform when nothing matches.
    """
    if not query_text.strip():
        return []
    lower = query_text.lower()
    matched: list[tuple[str, int]] = []
    for engine, keywords in _ENGINE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in lower)
        if hits > 0:
            matched.append((engine, hits))
    matched.sort(key=lambda t: t[1], reverse=True)
    engines = [engine for engine, _ in matched[:max_engines]]
    if not engines:
        engines = [_FALLBACK_ENGINE]
    return engines


def synthesize_responses(engine_responses: dict[str, str]) -> str:
    """Aggregate per-engine response strings into a single unified answer.

    Engine names are stripped from the output — the caller's responsibility
    is to pass response *content* as values, not engine-labeled strings.
    """
    if not engine_responses:
        return "No relevant information found for your query."
    parts = [v.strip() for v in engine_responses.values() if v.strip()]
    if not parts:
        return "No relevant information found for your query."
    if len(parts) == 1:
        return parts[0]
    return " ".join(parts)
