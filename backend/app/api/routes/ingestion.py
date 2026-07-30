from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.schedule_parser import ingest_schedule
from app.ingestion.document_ingester import ingest_single_document
from app.ingestion.boq_parser import ingest_boq
from app.agents.confidence_agent import recompute_all_scores

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/schedule")
async def upload_schedule(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a P6 XER or MS Project XML schedule file."""
    content = await file.read()
    result = ingest_schedule(content, file.filename, db)
    # Recompute all scores after schedule import
    recomputed = recompute_all_scores(db)
    result["scores_recomputed"] = recomputed
    return result


@router.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a single project document (PDF, DOCX, XLSX, TXT)."""
    content = await file.read()
    result = ingest_single_document(content, file.filename, db)
    if "evidence_item_id" in result:
        # Recompute scores for linked activities
        recompute_all_scores(db)
    return result


@router.post("/boq")
async def upload_boq(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a Bill of Quantities file (XLSX or CSV)."""
    content = await file.read()
    result = ingest_boq(content, file.filename, db)
    return result


@router.post("/recompute-all")
def trigger_recompute(db: Session = Depends(get_db)):
    """Recompute Evidence Score and Confidence Score for all activities."""
    count = recompute_all_scores(db)
    return {"recomputed": count}
