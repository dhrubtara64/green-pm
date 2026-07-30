"""
Evidence & Confidence Agent — computes Evidence Score (deterministic) and
Confidence Score (LLM-calibrated) for each Activity.

Evidence Score formula (logged for Product Council review):
  evidence_score = (count_score × 0.35) + (recency_score × 0.35) + (corroboration_score × 0.30)

  count_score      = min(distinct_source_count / 5, 1.0)  # saturates at 5 sources
  recency_score    = max(0, 1 - days_since_most_recent_evidence / 30)  # linear decay over 30 days
  corroboration_score = supporting / (supporting + contradicting)  # 0.5 if no evidence

  Source reliability signals are factored into Confidence Score, not Evidence Score.

Internally named "Evidence & Confidence Agent" — never exposed to users.
"""
import json
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.activity import Activity
from app.models.evidence_item import EvidenceItem, RelationType
from app.models.human_correction import HumanCorrection


def compute_evidence_score(evidence_items: list[EvidenceItem]) -> float:
    """Deterministic. No LLM. Counts, recency, corroboration."""
    if not evidence_items:
        return 0.0

    now = datetime.now(timezone.utc)

    # Component 1: distinct source count (saturates at 5)
    distinct_sources = len({e.source_system for e in evidence_items})
    count_score = min(distinct_sources / 5.0, 1.0)

    # Component 2: recency of most recent evidence item
    most_recent = max(e.timestamp for e in evidence_items)
    if most_recent.tzinfo is None:
        most_recent = most_recent.replace(tzinfo=timezone.utc)
    days_old = max(0, (now - most_recent).days)
    recency_score = max(0.0, 1.0 - (days_old / 30.0))

    # Component 3: corroboration ratio (supporting vs contradicting)
    supporting = sum(1 for e in evidence_items if e.relation_type == RelationType.supports_progress_of)
    contradicting = sum(1 for e in evidence_items if e.relation_type == RelationType.contradicts)
    total = supporting + contradicting
    corroboration_score = (supporting / total) if total > 0 else 0.5

    score = (count_score * 0.35) + (recency_score * 0.35) + (corroboration_score * 0.30)
    return round(min(max(score, 0.0), 1.0), 3)


def compute_confidence_score_llm(
    activity: Activity,
    evidence_items: list[EvidenceItem],
    evidence_score: float,
    correction_history: list[HumanCorrection],
    db: Session,
) -> tuple[float, str, list[str], str | None]:
    """
    LLM-calibrated confidence score.
    Returns (confidence_score, reasoning, evidence_refs, missing_evidence).

    Falls back to a heuristic if the Anthropic API key is not set.
    """
    if not settings.anthropic_api_key:
        return _heuristic_confidence(evidence_score, evidence_items), "Heuristic fallback (no API key set).", [], None

    reliability_map = {
        "high": "High (official approved documents, certified records)",
        "medium": "Medium (progress reports, internal trackers, vendor updates)",
        "low": "Low (informal updates, stale data, unverified field notes)",
        "unverified": "Unverified (first ingestion from this source, no track record)",
    }

    evidence_summary = []
    evidence_refs = []
    for e in evidence_items[:10]:
        rel = "SUPPORTS" if e.relation_type == RelationType.supports_progress_of else "CONTRADICTS"
        reliability = reliability_map.get(str(e.source_reliability_signal.value), "Unknown")
        now = datetime.now(timezone.utc)
        ts = e.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        days_old = (now - ts).days
        evidence_summary.append(
            f"  [{rel}] Source: {e.source_system} | Reliability: {reliability} | "
            f"Age: {days_old} days | Content: {e.extracted_content[:200]}"
        )
        evidence_refs.append(e.id)

    correction_summary = ""
    if correction_history:
        recent = correction_history[-3:]
        correction_summary = "\nPast human corrections on this activity:\n" + "\n".join(
            f"  - Field '{c.field_name}': {c.old_value} → {c.new_value} ({c.action})"
            for c in recent
        )

    has_contradiction = any(e.relation_type == RelationType.contradicts for e in evidence_items)

    system_prompt = """You are calibrating a Confidence Score for an EPC project activity.

The Evidence Score is a deterministic data-completeness metric (source count, recency, corroboration).
Your Confidence Score is your calibrated belief about whether the reported progress accurately
reflects the true state of work — factoring in source reliability history and interpretive ambiguity.

Key insight: A low Evidence Score with a high Confidence Score is a materially different signal
from a high Evidence Score with a low Confidence Score. Never collapse these into one number.

Return a JSON object with exactly this structure:
{
  "confidence_score": 0.XX,
  "reasoning": "One to two sentences explaining the key factor driving this score.",
  "missing_evidence": "Specific named gap (e.g. 'No approved inspection record for concrete pour') or null if none.",
  "evidence_refs": ["ev-id-1", "ev-id-2"]
}

Rules:
- confidence_score must be a float between 0.0 and 1.0
- Be honest: if evidence is thin or unreliable, say so
- Never claim certainty you don't have
- Return only valid JSON, no text outside the JSON object"""

    user_message = f"""Activity: {activity.name}
WBS Reference: {activity.wbs_ref or "N/A"}
Reported Progress: {activity.reported_progress}%
Evidence Score (deterministic): {evidence_score}
Contradicting evidence present: {"YES" if has_contradiction else "No"}

Evidence items ({len(evidence_items)} total):
{chr(10).join(evidence_summary) if evidence_summary else "  (none)"}
{correction_summary}

Compute the Confidence Score for this activity."""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON in response")
        result = json.loads(json_match.group())

        score = float(result.get("confidence_score", 0.5))
        score = round(min(max(score, 0.0), 1.0), 3)
        reasoning = result.get("reasoning", "")
        missing = result.get("missing_evidence")
        refs = result.get("evidence_refs", evidence_refs)

        return score, reasoning, refs, missing

    except Exception as ex:
        fallback = _heuristic_confidence(evidence_score, evidence_items)
        return fallback, f"LLM call failed ({ex}); using heuristic.", evidence_refs, None


def _heuristic_confidence(evidence_score: float, evidence_items: list[EvidenceItem]) -> float:
    """Fallback when LLM is unavailable — degrades evidence_score by reliability."""
    if not evidence_items:
        return 0.0
    reliability_weights = {"high": 1.0, "medium": 0.75, "low": 0.4, "unverified": 0.5}
    avg_reliability = sum(
        reliability_weights.get(str(e.source_reliability_signal.value), 0.5)
        for e in evidence_items
    ) / len(evidence_items)
    return round(evidence_score * avg_reliability, 3)


def recompute_activity_scores(activity_id: str, db: Session) -> Activity:
    """
    Recomputes Evidence Score and Confidence Score for an Activity.
    Called whenever an EvidenceItem is added, confirmed, or corrected.
    """
    activity = db.get(Activity, activity_id)
    if not activity:
        raise ValueError(f"Activity not found: {activity_id}")

    evidence_items = activity.evidence_items
    correction_history = activity.corrections

    # Step 1: Evidence Score (deterministic)
    evidence_score = compute_evidence_score(evidence_items)
    activity.evidence_score = evidence_score

    # Step 2: Confidence Score (LLM-calibrated)
    result = compute_confidence_score_llm(
        activity=activity,
        evidence_items=evidence_items,
        evidence_score=evidence_score,
        correction_history=correction_history,
        db=db,
    )

    confidence_score, reasoning, evidence_refs, missing_evidence = result

    activity.confidence_score = confidence_score
    activity.confidence_reasoning = reasoning
    if missing_evidence:
        activity.missing_evidence = missing_evidence

    # Step 3: Determine verification_required
    has_contradiction = any(
        e.relation_type == RelationType.contradicts for e in evidence_items
    )
    activity.verification_required = (
        has_contradiction
        or (evidence_score < 0.25 and confidence_score < 0.30)
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def recompute_all_scores(db: Session) -> int:
    """Recompute scores for all activities. Used after bulk ingestion."""
    activities = db.query(Activity).all()
    for activity in activities:
        recompute_activity_scores(activity.id, db)
    return len(activities)
