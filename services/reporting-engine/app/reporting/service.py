"""Reporting Engine service layer — S17-01, S17-04, S17-05."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.reporting.model import Report
from app.reporting.schemas import ReportCreate

_NARRATIVE_SYSTEM_PROMPT: str = (
    "You are a project reporting assistant for Green PM. "
    "Write a concise, evidence-grounded narrative section for the project report. "
    "Cite the nature of data informing each claim. Be factual and direct."
)


class ReportNotFoundError(Exception):
    pass


async def create_report(
    session,
    tenant_id: uuid.UUID,
    create: ReportCreate,
) -> Report:
    record = Report(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=create.project_id,
        report_type=create.report_type,
        title=create.title,
        structured_data=create.structured_data,
        status="PENDING",
        scheduled=create.scheduled,
    )
    session.add(record)
    await session.flush()
    return record


async def generate_report(
    session,
    tenant_id: uuid.UUID,
    report_id: uuid.UUID,
    ai_client=None,
    context_hint: Optional[str] = None,
) -> Report:
    """Generate AI narrative for an existing report and mark it COMPLETE — S17-01.

    ai_client is dependency-injected; when None a stub narrative is used,
    so all unit tests run without a real Claude API call.
    """
    record = await get_report(session, tenant_id, report_id)
    record.status = "GENERATING"
    await session.flush()

    chain_id = uuid.uuid4()

    if ai_client is not None:
        prompt = (
            f"Generate a narrative section for a {record.report_type} report titled "
            f"'{record.title}'. "
        )
        if context_hint:
            prompt += f"Context: {context_hint}. "
        prompt += f"Structured data summary: {record.structured_data or {}}."
        try:
            narrative = await ai_client.complete(prompt)
        except Exception:
            record.status = "FAILED"
            await session.flush()
            raise
    else:
        narrative = (
            f"Report narrative for {record.report_type}: {record.title}. "
            "All project metrics reviewed. Key findings attached."
        )

    record.narrative = narrative
    record.evidence_chain_id = chain_id
    record.status = "COMPLETE"
    record.generated_at = datetime.now(timezone.utc)
    await session.flush()
    return record


async def list_reports(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    report_type: Optional[str] = None,
) -> list[Report]:
    stmt = select(Report).where(
        Report.tenant_id == tenant_id,
        Report.project_id == project_id,
    )
    if report_type is not None:
        stmt = stmt.where(Report.report_type == report_type)
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_report(
    session,
    tenant_id: uuid.UUID,
    report_id: uuid.UUID,
) -> Report:
    stmt = select(Report).where(
        Report.tenant_id == tenant_id,
        Report.id == report_id,
    )
    record = await session.scalar(stmt)
    if record is None:
        raise ReportNotFoundError(f"Report {report_id} not found")
    return record


async def schedule_report(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    report_type: str,
    title: Optional[str] = None,
) -> Report:
    """Create a scheduled report record — triggered by Cloud Scheduler (S17-05)."""
    create = ReportCreate(
        project_id=project_id,
        report_type=report_type,
        title=title or f"Scheduled {report_type.replace('_', ' ').title()}",
        scheduled=True,
    )
    return await create_report(session, tenant_id, create)
