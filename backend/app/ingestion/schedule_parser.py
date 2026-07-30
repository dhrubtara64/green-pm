"""
Parses Primavera P6 XER exports and basic MS Project XML files into
Activity and Milestone records.

P6 XER format is tab-delimited with sections:
  %T  TABLENAME
  %F  field1\tfield2\t...
  %R  val1\tval2\t...

MS Project XML exports the <Project><Tasks><Task>...</Task></Tasks></Project> structure.
"""
import io
import re
import uuid
from datetime import datetime, timezone
from typing import IO

from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.milestone import Milestone
from app.models.associations import activity_milestones


def _parse_p6_xer(content: str) -> tuple[list[dict], list[dict]]:
    """Returns (activities, milestones) as lists of dicts from a P6 XER export."""
    tables: dict[str, list[dict]] = {}
    current_table = None
    current_fields: list[str] = []

    for line in content.splitlines():
        if line.startswith("%T"):
            current_table = line[2:].strip()
            tables[current_table] = []
        elif line.startswith("%F"):
            current_fields = line[2:].strip().split("\t")
        elif line.startswith("%R") and current_table:
            values = line[2:].strip().split("\t")
            row = dict(zip(current_fields, values))
            tables[current_table].append(row)
        elif line.startswith("%E"):
            current_table = None

    activities = []
    milestones = []
    task_rows = tables.get("TASK", [])

    for row in task_rows:
        task_type = row.get("task_type", "TT_Task")
        name = row.get("task_name", "Unnamed Activity")
        task_id = row.get("task_id", str(uuid.uuid4()))
        wbs_id = row.get("wbs_id", "")

        # Parse progress
        phys_complete = row.get("phys_complete_pct", "0")
        try:
            progress = float(phys_complete)
        except ValueError:
            progress = 0.0

        if task_type in ("TT_Mile", "TT_FinMile"):
            target_date_str = row.get("act_end_date") or row.get("target_end_date") or ""
            target_date = _parse_p6_date(target_date_str)
            milestones.append({
                "id": f"ms-{task_id}",
                "name": name,
                "target_date": target_date,
                "description": f"WBS: {wbs_id}",
            })
        else:
            activities.append({
                "id": f"act-{task_id}",
                "name": name,
                "wbs_ref": wbs_id,
                "source_schedule_ref": task_id,
                "reported_progress": progress,
            })

    return activities, milestones


def _parse_p6_date(s: str):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None


def _parse_msproject_xml(content: str) -> tuple[list[dict], list[dict]]:
    """Parse a basic MS Project XML export."""
    try:
        from lxml import etree as ET
    except ImportError:
        import xml.etree.ElementTree as ET

    activities = []
    milestones = []

    try:
        root = ET.fromstring(content.encode())
    except Exception:
        return activities, milestones

    ns = {"ms": "http://schemas.microsoft.com/project"}

    def find_text(el, tag):
        child = el.find(f"ms:{tag}", ns) or el.find(tag)
        return child.text if child is not None else ""

    tasks_el = root.find("ms:Tasks", ns) or root.find("Tasks")
    if tasks_el is None:
        return activities, milestones

    for task in tasks_el.findall("ms:Task", ns) or tasks_el.findall("Task"):
        uid = find_text(task, "UID")
        name = find_text(task, "Name") or "Unnamed Activity"
        is_milestone = find_text(task, "Milestone") in ("1", "true", "True")
        pct_complete = find_text(task, "PercentComplete") or "0"
        outline = find_text(task, "OutlineNumber") or ""
        finish = find_text(task, "Finish") or ""

        try:
            progress = float(pct_complete)
        except ValueError:
            progress = 0.0

        if is_milestone:
            target_date = None
            if finish:
                try:
                    target_date = datetime.fromisoformat(finish[:10]).date()
                except ValueError:
                    pass
            milestones.append({
                "id": f"ms-{uid}",
                "name": name,
                "target_date": target_date,
                "description": f"Outline: {outline}",
            })
        else:
            activities.append({
                "id": f"act-{uid}",
                "name": name,
                "wbs_ref": outline,
                "source_schedule_ref": uid,
                "reported_progress": progress,
            })

    return activities, milestones


def ingest_schedule(
    file_content: bytes,
    filename: str,
    db: Session,
) -> dict:
    """
    Ingests a P6 XER or MS Project XML schedule file.
    Returns a summary dict of what was created/updated.
    """
    content_str = file_content.decode("utf-8", errors="replace")

    if filename.lower().endswith(".xer"):
        raw_activities, raw_milestones = _parse_p6_xer(content_str)
    elif filename.lower().endswith((".xml", ".mpp")):
        raw_activities, raw_milestones = _parse_msproject_xml(content_str)
    else:
        # Try XER format first, fall back to XML
        if "%T" in content_str and "%F" in content_str:
            raw_activities, raw_milestones = _parse_p6_xer(content_str)
        else:
            raw_activities, raw_milestones = _parse_msproject_xml(content_str)

    created_activities = 0
    updated_activities = 0
    created_milestones = 0

    for a in raw_activities:
        existing = db.get(Activity, a["id"])
        if existing:
            existing.reported_progress = a["reported_progress"]
            existing.wbs_ref = a.get("wbs_ref")
            existing.source_schedule_ref = a.get("source_schedule_ref")
            updated_activities += 1
        else:
            db.add(Activity(
                id=a["id"],
                name=a["name"],
                wbs_ref=a.get("wbs_ref"),
                source_schedule_ref=a.get("source_schedule_ref"),
                reported_progress=a["reported_progress"],
            ))
            created_activities += 1

    for m in raw_milestones:
        existing = db.get(Milestone, m["id"])
        if not existing:
            db.add(Milestone(
                id=m["id"],
                name=m["name"],
                target_date=m.get("target_date"),
                description=m.get("description"),
            ))
            created_milestones += 1

    db.commit()
    return {
        "filename": filename,
        "activities_created": created_activities,
        "activities_updated": updated_activities,
        "milestones_created": created_milestones,
    }
