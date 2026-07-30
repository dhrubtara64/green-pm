import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.activity import Activity
from app.models.human_correction import HumanCorrection
from app.schemas.activity import ActivitySummary, ActivityDetail, ConfirmRequest, CorrectRequest, CorrectionOut
from app.agents.confidence_agent import recompute_activity_scores

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("/", response_model=list[ActivitySummary])
def list_activities(db: Session = Depends(get_db)):
    return db.query(Activity).order_by(Activity.wbs_ref, Activity.name).all()


@router.get("/{activity_id}", response_model=ActivityDetail)
def get_activity(activity_id: str, db: Session = Depends(get_db)):
    activity = db.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.post("/{activity_id}/confirm", response_model=CorrectionOut)
def confirm_inference(
    activity_id: str,
    req: ConfirmRequest,
    db: Session = Depends(get_db),
):
    """Human confirms an AI inference — logs the confirmation."""
    activity = db.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    correction = HumanCorrection(
        id=f"corr-{uuid.uuid4().hex[:12]}",
        activity_id=activity_id,
        field_name=req.field_name,
        old_value=req.current_value,
        new_value=req.current_value,
        action="confirm",
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)
    return correction


@router.post("/{activity_id}/correct", response_model=ActivityDetail)
def correct_inference(
    activity_id: str,
    req: CorrectRequest,
    db: Session = Depends(get_db),
):
    """Human corrects an AI inference — updates the activity and logs the change."""
    activity = db.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Log the correction
    correction = HumanCorrection(
        id=f"corr-{uuid.uuid4().hex[:12]}",
        activity_id=activity_id,
        field_name=req.field_name,
        old_value=req.old_value,
        new_value=req.new_value,
        action="correct",
        rationale=req.rationale,
    )
    db.add(correction)

    # Apply the correction to the activity
    if req.field_name == "reported_progress":
        try:
            activity.reported_progress = float(req.new_value)
        except ValueError:
            pass
    elif req.field_name == "missing_evidence":
        activity.missing_evidence = req.new_value
    elif req.field_name == "confidence_score":
        try:
            activity.confidence_score = float(req.new_value)
        except ValueError:
            pass

    db.add(activity)
    db.commit()

    # Recompute scores after human correction
    updated = recompute_activity_scores(activity_id, db)
    return updated


@router.post("/{activity_id}/recompute")
def recompute_scores(activity_id: str, db: Session = Depends(get_db)):
    """Trigger score recomputation for a single activity."""
    try:
        updated = recompute_activity_scores(activity_id, db)
        return {
            "activity_id": activity_id,
            "evidence_score": updated.evidence_score,
            "confidence_score": updated.confidence_score,
            "verification_required": updated.verification_required,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
