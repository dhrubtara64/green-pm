from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.project import Project

from .schemas import ProjectCreate, ProjectUpdate


class ProjectNotFoundError(Exception):
    def __init__(self, project_id: uuid.UUID) -> None:
        super().__init__(f"Project {project_id} not found")


class ProjectCodeConflictError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(f"Project code already exists in this tenant: {code!r}")


async def create_project(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: ProjectCreate,
) -> Project:
    existing = await session.scalar(
        select(Project).where(
            and_(Project.tenant_id == tenant_id, Project.project_code == data.project_code)
        )
    )
    if existing is not None:
        raise ProjectCodeConflictError(data.project_code)

    project = Project(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=data.name,
        project_code=data.project_code,
        status=data.status,
    )
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return project


async def get_project(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Project:
    project = await session.scalar(
        select(Project).where(
            and_(Project.id == project_id, Project.tenant_id == tenant_id)
        )
    )
    if project is None:
        raise ProjectNotFoundError(project_id)
    return project


async def list_projects(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Project]:
    query = (
        select(Project)
        .where(Project.tenant_id == tenant_id)
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status is not None:
        query = query.where(Project.status == status)
    result = await session.execute(query)
    return result.scalars().all()


async def update_project(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    data: ProjectUpdate,
) -> Project:
    project = await get_project(session, tenant_id, project_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await session.flush()
    await session.refresh(project)
    return project
