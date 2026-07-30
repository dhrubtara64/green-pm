import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.weekly_report import WeeklyReport
from app.schemas.report import ReportOut, ReportEditRequest
from app.agents.communication_agent import draft_weekly_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db)):
    return db.query(WeeklyReport).order_by(WeeklyReport.created_at.desc()).limit(10).all()


@router.post("/draft", response_model=ReportOut)
def create_draft(db: Session = Depends(get_db)):
    """Generate a new weekly report draft from current project state."""
    report = draft_weekly_report(db)
    return report


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.get(WeeklyReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.patch("/{report_id}", response_model=ReportOut)
def edit_report(
    report_id: str,
    req: ReportEditRequest,
    db: Session = Depends(get_db),
):
    """Save a human-edited version of the report."""
    report = db.get(WeeklyReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.edited_content = req.edited_content
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("/{report_id}/send")
def send_report(report_id: str, db: Session = Depends(get_db)):
    """
    'Send' the report — V1: logs the action only. No real email is sent.
    A human must explicitly click this; nothing is sent autonomously.
    """
    report = db.get(WeeklyReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.confirmed_at = datetime.now(timezone.utc)
    report.send_log = json.dumps({
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "action": "send_requested",
        "note": "V1: No real email sent. Action logged for audit trail.",
    })
    db.add(report)
    db.commit()
    return {"status": "logged", "message": "Report send action logged. No email was sent (V1 — no outbound integration)."}
