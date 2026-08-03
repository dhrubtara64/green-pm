"""Activity Workspace API router — S2-WS-01."""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import ActivityCreate, ActivityResponse, ActivityUpdate
from .service import ActivityNotFoundError, create_activity, get_activity, list_activities, update_activity

router = APIRouter(prefix="/activities", tags=["activities"])


async def _get_session() -> AsyncSession:
    raise NotImplementedError("Inject a real session provider at app startup")


SessionDep = Annotated[AsyncSession, Depends(_get_session)]


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity_endpoint(
    body: ActivityCreate,
    tenant_id: uuid.UUID,
    session: SessionDep,
) -> ActivityResponse:
    activity = await create_activity(session, tenant_id, body)
    return ActivityResponse.model_validate(activity)


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity_endpoint(
    activity_id: uuid.UUID,
    tenant_id: uuid.UUID,
    session: SessionDep,
) -> ActivityResponse:
    try:
        activity = await get_activity(session, tenant_id, activity_id)
    except ActivityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ActivityResponse.model_validate(activity)


@router.get("", response_model=list[ActivityResponse])
async def list_activities_endpoint(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    session: SessionDep,
    activity_status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[ActivityResponse]:
    activities = await list_activities(
        session, tenant_id, project_id,
        status=activity_status, limit=limit, offset=offset,
    )
    return [ActivityResponse.model_validate(a) for a in activities]


@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity_endpoint(
    activity_id: uuid.UUID,
    body: ActivityUpdate,
    tenant_id: uuid.UUID,
    session: SessionDep,
) -> ActivityResponse:
    try:
        activity = await update_activity(session, tenant_id, activity_id, body)
    except ActivityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ActivityResponse.model_validate(activity)
