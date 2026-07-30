"""
Conversational Orchestrator — scoped to a single selected Activity.
Answers questions about one activity's evidence and confidence only.

V1 scope: "why is this activity's confidence low?", "what evidence supports this?",
"what's missing for this activity?" — NOT open-ended project-wide questions.

Branded as "Green PM AI" only. Never exposes agent or module names.
"""
import json
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.activity import Activity
from app.models.evidence_item import RelationType


SYSTEM_PROMPT = """You are Green PM AI, an assistant that helps project controls teams understand
the evidence and confidence behind individual project activity statuses.

Your scope is strictly limited to questions about the specific activity you've been given context for.
Do not answer questions about other activities, the broader project schedule, or topics outside
the evidence and confidence scoring for this activity.

When you answer:
1. Always cite specific evidence items by their ID when they support your answer
2. Be honest about uncertainty — if evidence is thin, say so
3. Never claim more confidence than the Evidence Score and Confidence Score justify
4. Recommend human review for Verification Required activities
5. Phrase everything as "based on the evidence sourced from your project documents/schedule"
6. Never mention internal agent names, modules, or the word "agent" — you are Green PM AI

If a question is outside your scope (e.g., "What about the other activities?"),
politely redirect: "I'm focused on [activity name] right now. For a full project view,
please use the main dashboard."

Return a JSON response with:
{
  "answer": "Your response to the user",
  "evidence_refs": ["ev-id-1", "ev-id-2"]  // IDs of evidence items you cited
}"""


def answer_activity_question(
    activity_id: str,
    user_message: str,
    conversation_history: list[dict],
    db: Session,
) -> dict:
    """
    Answers a user question scoped to a single activity.
    Returns {"answer": str, "evidence_refs": list[str]}.
    """
    activity = db.get(Activity, activity_id)
    if not activity:
        return {"answer": "Activity not found.", "evidence_refs": []}

    evidence_items = activity.evidence_items
    reliability_map = {
        "high": "High", "medium": "Medium", "low": "Low", "unverified": "Unverified"
    }

    evidence_detail = []
    for e in evidence_items[:10]:
        rel = "supports" if e.relation_type == RelationType.supports_progress_of else "CONTRADICTS"
        now = datetime.now(timezone.utc)
        ts = e.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        days_old = (now - ts).days
        evidence_detail.append(
            f"[{e.id}] {rel} | from {e.source_system} | "
            f"reliability: {reliability_map.get(str(e.source_reliability_signal.value), '?')} | "
            f"age: {days_old} days | {e.extracted_content[:150]}"
        )

    context_block = f"""ACTIVITY CONTEXT:
Name: {activity.name}
WBS: {activity.wbs_ref or "N/A"}
Reported Progress: {activity.reported_progress:.0f}%
Evidence Score: {activity.evidence_score:.2f} (0=no evidence, 1=fully corroborated)
Confidence Score: {activity.confidence_score:.2f} (0=very uncertain, 1=highly confident)
Verification Required: {"YES — human review needed before reporting" if activity.verification_required else "No"}
Missing Evidence: {activity.missing_evidence or "None identified"}
AI Reasoning: {activity.confidence_reasoning or "Not yet computed"}

Evidence items ({len(evidence_items)} total):
{chr(10).join(evidence_detail) if evidence_detail else "None — no evidence linked to this activity yet."}"""

    # Build message history for the API call
    messages = []
    for msg in conversation_history[-6:]:  # keep last 6 turns
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Inject context into the first message if this is the start of a conversation
    if not messages:
        messages.append({
            "role": "user",
            "content": f"{context_block}\n\n---\n\n{user_message}",
        })
    else:
        # Prepend context as a system-level update to the latest user message
        messages.append({
            "role": "user",
            "content": f"[Current activity context refreshed]\n{context_block}\n\n---\n\n{user_message}",
        })

    if not settings.anthropic_api_key:
        answer = _fallback_answer(activity, user_message, evidence_items)
        return {"answer": answer, "evidence_refs": [e.id for e in evidence_items[:3]]}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        raw = response.content[0].text.strip()

        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "answer": result.get("answer", raw),
                "evidence_refs": result.get("evidence_refs", []),
            }
        else:
            return {"answer": raw, "evidence_refs": []}

    except Exception as ex:
        answer = _fallback_answer(activity, user_message, evidence_items)
        return {"answer": f"{answer}\n\n_(Green PM AI unavailable: {ex})_", "evidence_refs": []}


def _fallback_answer(activity, user_message: str, evidence_items) -> str:
    """Plain-text fallback when LLM is unavailable."""
    msg_lower = user_message.lower()

    if "evidence" in msg_lower or "what support" in msg_lower:
        if not evidence_items:
            return (
                f"No evidence has been linked to **{activity.name}** yet. "
                f"The Evidence Score is {activity.evidence_score:.2f}. "
                "Try ingesting the project document folder to populate evidence."
            )
        ev_list = "\n".join(f"- [{e.id}] {e.source_system}: {e.extracted_content[:100]}" for e in evidence_items[:5])
        return f"Evidence sourced from your project documents for **{activity.name}**:\n{ev_list}"

    if "confidence" in msg_lower or "why" in msg_lower or "low" in msg_lower:
        return (
            f"**{activity.name}** has an Evidence Score of {activity.evidence_score:.2f} "
            f"and a Confidence Score of {activity.confidence_score:.2f}. "
            f"{activity.confidence_reasoning or 'No reasoning available — run score recompute to generate AI reasoning.'}"
        )

    if "missing" in msg_lower:
        return (
            f"Missing evidence for **{activity.name}**: "
            f"{activity.missing_evidence or 'No specific gaps identified yet.'}"
        )

    return (
        f"**{activity.name}** — Progress: {activity.reported_progress:.0f}% | "
        f"Evidence Score: {activity.evidence_score:.2f} | "
        f"Confidence: {activity.confidence_score:.2f} | "
        f"{'⚠ Verification Required' if activity.verification_required else 'No flags'}"
    )
