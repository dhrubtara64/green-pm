"""
Evidence Agent — classifies ingested documents and links EvidenceItems to
Activities and Deliverables in the graph.

Internally named "Evidence Agent" — never exposed to users.
All user-facing AI is branded "Green PM AI."
"""
import json
import re
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.activity import Activity
from app.models.deliverable import Deliverable
from app.models.associations import activity_evidence_items, deliverable_evidence_items


def _get_anthropic():
    import anthropic
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def classify_and_link_document(
    evidence_item_id: str,
    filename: str,
    extracted_text: str,
    db: Session,
) -> int:
    """
    Uses Claude to classify which activities/deliverables an ingested document
    relates to and creates the appropriate join table rows.

    Returns the number of entities linked.
    """
    if not settings.anthropic_api_key:
        return 0

    # Get current activities and deliverables for matching
    activities = db.query(Activity).all()
    deliverables = db.query(Deliverable).all()

    if not activities and not deliverables:
        return 0

    activity_list = "\n".join(f"- id:{a.id} | {a.name} (WBS: {a.wbs_ref})" for a in activities[:30])
    deliverable_list = "\n".join(f"- id:{d.id} | {d.name} (type: {d.type})" for d in deliverables[:20])

    system_prompt = """You are classifying a project document to determine which project activities
and deliverables it provides evidence for. You must cite your reasoning.

Return a JSON object with this exact structure:
{
  "activity_links": [
    {"activity_id": "...", "relation_type": "supports_progress_of|contradicts", "reason": "..."}
  ],
  "deliverable_links": [
    {"deliverable_id": "...", "relation_type": "supports_progress_of|contradicts", "reason": "..."}
  ]
}

Rules:
- Only link to entities listed in the available activities/deliverables.
- Use "contradicts" if the document suggests different status than what would be expected.
- Limit to the 3 most relevant matches for activities and 2 for deliverables.
- Return an empty list if no clear match exists — do not guess.
- Your response must be valid JSON only, no explanation outside the JSON."""

    user_message = f"""Document filename: {filename}

Available activities:
{activity_list}

Available deliverables:
{deliverable_list}

Document content (first 2000 chars):
{extracted_text[:2000]}

Classify which activities and deliverables this document provides evidence for."""

    try:
        client = _get_anthropic()
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()

        # Extract JSON even if there's surrounding text
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            return 0
        result = json.loads(json_match.group())

    except Exception:
        return 0

    linked = 0

    for link in result.get("activity_links", []):
        activity_id = link.get("activity_id", "")
        relation_type = link.get("relation_type", "supports_progress_of")
        if relation_type not in ("supports_progress_of", "contradicts"):
            relation_type = "supports_progress_of"

        # Verify activity exists
        activity = db.get(Activity, activity_id)
        if not activity:
            continue

        # Avoid duplicate links
        existing = db.execute(
            text("SELECT 1 FROM activity_evidence_items WHERE activity_id=:aid AND evidence_item_id=:eid"),
            {"aid": activity_id, "eid": evidence_item_id},
        ).fetchone()

        if not existing:
            db.execute(
                activity_evidence_items.insert().values(
                    activity_id=activity_id,
                    evidence_item_id=evidence_item_id,
                    relation_type=relation_type,
                )
            )
            linked += 1

    for link in result.get("deliverable_links", []):
        deliverable_id = link.get("deliverable_id", "")
        relation_type = link.get("relation_type", "supports_progress_of")
        if relation_type not in ("supports_progress_of", "contradicts"):
            relation_type = "supports_progress_of"

        deliverable = db.get(Deliverable, deliverable_id)
        if not deliverable:
            continue

        existing = db.execute(
            text("SELECT 1 FROM deliverable_evidence_items WHERE deliverable_id=:did AND evidence_item_id=:eid"),
            {"did": deliverable_id, "eid": evidence_item_id},
        ).fetchone()

        if not existing:
            db.execute(
                deliverable_evidence_items.insert().values(
                    deliverable_id=deliverable_id,
                    evidence_item_id=evidence_item_id,
                    relation_type=relation_type,
                )
            )
            linked += 1

    return linked
