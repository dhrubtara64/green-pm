"""
BOQ (Bill of Quantities) spreadsheet ingestion.
Parses xlsx/csv BOQ files, creates EvidenceItems for each line item,
and links them to Deliverables/Activities where identifiable.
"""
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.evidence_item import EvidenceItem, SourceReliabilitySignal, RelationType
from app.models.deliverable import Deliverable
from app.models.associations import deliverable_evidence_items


def _parse_boq_xlsx(content: bytes) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows = []
    for sheet in wb.worksheets:
        headers = []
        for i, row in enumerate(sheet.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(c).strip() if c else f"col_{j}" for j, c in enumerate(row)]
                continue
            if all(c is None for c in row):
                continue
            rows.append(dict(zip(headers, row)))
    return rows


def _parse_boq_csv(content: bytes) -> list[dict]:
    import csv
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _find_matching_deliverable(row: dict, db: Session) -> Deliverable | None:
    """Heuristic match: look for a deliverable whose name appears in BOQ line item description."""
    description = ""
    for key in ("description", "Description", "item", "Item", "name", "Name", "work_item", "Work Item"):
        if key in row and row[key]:
            description = str(row[key]).lower()
            break

    if not description:
        return None

    deliverables = db.query(Deliverable).all()
    for d in deliverables:
        if d.name.lower() in description or description in d.name.lower():
            return d
    return None


def ingest_boq(
    content: bytes,
    filename: str,
    db: Session,
) -> dict:
    """
    Parse a BOQ file and create EvidenceItems for each line item.
    Link to Deliverables where a name match is found.
    """
    ext = Path(filename).suffix.lower()
    if ext in (".xlsx", ".xls"):
        rows = _parse_boq_xlsx(content)
    elif ext == ".csv":
        rows = _parse_boq_csv(content)
    else:
        return {"error": f"Unsupported BOQ format: {ext}. Use xlsx or csv."}

    items_created = 0
    items_linked = 0

    for i, row in enumerate(rows):
        # Build a human-readable summary of this BOQ line item
        summary_parts = [f"{k}: {v}" for k, v in row.items() if v]
        summary = " | ".join(summary_parts[:8])  # cap at 8 fields for readability

        if not summary.strip():
            continue

        item_id = f"ev-boq-{uuid.uuid4().hex[:12]}"
        evidence_item = EvidenceItem(
            id=item_id,
            source_system="boq_upload",
            ingesting_connector="boq_ingestor_v1",
            provenance_ref=f"{filename}:row_{i+2}",
            extracted_content=summary,
            source_excerpt=summary[:200],
            relation_type=RelationType.supports_progress_of,
            source_reliability_signal=SourceReliabilitySignal.medium,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(evidence_item)
        db.flush()
        items_created += 1

        # Try to link to a Deliverable
        matched_deliverable = _find_matching_deliverable(row, db)
        if matched_deliverable:
            db.execute(
                deliverable_evidence_items.insert().values(
                    deliverable_id=matched_deliverable.id,
                    evidence_item_id=item_id,
                    relation_type="supports_progress_of",
                )
            )
            items_linked += 1

    db.commit()
    return {
        "filename": filename,
        "rows_processed": len(rows),
        "items_created": items_created,
        "items_linked_to_deliverables": items_linked,
    }
