"""
Communication Agent — drafts the weekly/steering-committee progress report
from current graph state.

One template only (V1). Human must edit and confirm before "send."
"Send" is always a logged no-op in V1 — no real email sent.

Internally named "Communication Agent" — never exposed to users.
"""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.activity import Activity
from app.models.weekly_report import WeeklyReport


def draft_weekly_report(db: Session) -> WeeklyReport:
    """
    Drafts a weekly progress report from current Activity scores and evidence.
    Returns an unsaved WeeklyReport object (caller must commit).
    """
    activities = db.query(Activity).order_by(Activity.wbs_ref).all()

    if not activities:
        draft = "No activities found in the project. Please ingest a schedule first."
        return WeeklyReport(
            id=f"rpt-{uuid.uuid4().hex[:12]}",
            draft_content=draft,
        )

    # Build a structured summary for the LLM to work from
    activity_summaries = []
    verification_flags = []
    low_confidence = []

    for a in activities:
        status = "✓ Confirmed" if a.confidence_score >= 0.65 else "⚠ Review"
        if a.verification_required:
            status = "🔴 Verification Required"
            verification_flags.append(a.name)
        if a.confidence_score < 0.50:
            low_confidence.append(a.name)

        evidence_count = len(a.evidence_items)
        summary = (
            f"  - {a.name} ({a.wbs_ref or 'No WBS'}): "
            f"{a.reported_progress:.0f}% complete | "
            f"Evidence Score: {a.evidence_score:.2f} | "
            f"Confidence: {a.confidence_score:.2f} | "
            f"Evidence items: {evidence_count} | {status}"
        )
        if a.missing_evidence:
            summary += f"\n    Missing: {a.missing_evidence}"
        activity_summaries.append(summary)

    activities_text = "\n".join(activity_summaries)
    snapshot = {
        "total_activities": len(activities),
        "verification_required": len(verification_flags),
        "low_confidence": len(low_confidence),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if not settings.anthropic_api_key:
        draft = _fallback_report(activities, verification_flags, low_confidence, activities_text)
        return WeeklyReport(
            id=f"rpt-{uuid.uuid4().hex[:12]}",
            draft_content=draft,
            activities_snapshot=json.dumps(snapshot),
        )

    system_prompt = """You are drafting a weekly engineering project progress report for an EPC project.

This report will be reviewed and edited by the project controls team before being sent to the steering committee.
Write it clearly and professionally. Never use agent or module names — all insights are from "Green PM AI."

Important rules:
- Frame all insights as sourced from the project's own schedule, documents, and BOQ — never claim Green PM generated the data
- Express honest uncertainty where confidence scores are low
- For activities flagged "Verification Required," state clearly that human review is needed before reporting
- One concise sentence per activity in the status table
- End with a named action list for the project team

Format the report as structured markdown."""

    user_message = f"""Project status as of {datetime.now(timezone.utc).strftime('%d %B %Y')}

Activity Status Summary (sourced from schedule and project documents):
{activities_text}

Flags:
- Verification Required: {', '.join(verification_flags) if verification_flags else 'None'}
- Low Confidence (<50%): {', '.join(low_confidence) if low_confidence else 'None'}

Draft a weekly steering committee progress report. Include:
1. Executive Summary (3-4 sentences)
2. Progress Table (activity name, reported %, confidence level, status)
3. Key Risks and Flags (activities needing human review)
4. Action Items for this week
5. Note: "Reviewed and confirmed by: __________ Date: __________"

Remind the reader that this draft requires human review before distribution."""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        draft = response.content[0].text.strip()
    except Exception as ex:
        draft = _fallback_report(activities, verification_flags, low_confidence, activities_text)
        draft += f"\n\n_(Report drafted without AI assistance: {ex})_"

    report = WeeklyReport(
        id=f"rpt-{uuid.uuid4().hex[:12]}",
        draft_content=draft,
        activities_snapshot=json.dumps(snapshot),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _fallback_report(activities, verification_flags, low_confidence, activities_text) -> str:
    """Plain-text report when LLM is unavailable."""
    now = datetime.now(timezone.utc).strftime("%d %B %Y")
    lines = [
        f"# Weekly Project Progress Report — {now}",
        "",
        "**DRAFT — Requires human review before distribution**",
        "",
        "## Executive Summary",
        f"This report covers {len(activities)} activities sourced from the project schedule and documents.",
        f"{len(verification_flags)} activities require verification before reporting.",
        f"{len(low_confidence)} activities have low confidence scores.",
        "",
        "## Activity Status",
        activities_text,
        "",
        "## Items Requiring Human Review",
    ]
    if verification_flags:
        for name in verification_flags:
            lines.append(f"- 🔴 {name}: Conflicting or insufficient evidence — do not report without verification")
    else:
        lines.append("- None flagged")

    lines += [
        "",
        "## Action Items",
        "- [ ] Review all Verification Required activities with site team",
        "- [ ] Confirm or correct low-confidence activity progress",
        "- [ ] Approve this report before distribution",
        "",
        "_Reviewed and confirmed by: __________ Date: __________",
    ]
    return "\n".join(lines)
