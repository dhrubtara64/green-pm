from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.activity import Activity
from app.schemas.chat import ChatRequest, ChatResponse
from app.agents.orchestrator import answer_activity_question

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Green PM AI — answers questions about a specific activity's evidence and confidence.
    Scoped to one activity; does not answer project-wide questions (V1).
    """
    activity = db.get(Activity, req.activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    history = [{"role": m.role, "content": m.content} for m in req.history]

    result = answer_activity_question(
        activity_id=req.activity_id,
        user_message=req.message,
        conversation_history=history,
        db=db,
    )
    return ChatResponse(
        answer=result["answer"],
        evidence_refs=result.get("evidence_refs", []),
    )
