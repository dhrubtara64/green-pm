from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import TenantCreate, TenantResponse, TenantUpdate
from .service import (
    TenantNameConflictError,
    TenantNotFoundError,
    create_tenant,
    deactivate_tenant,
    get_tenant,
    list_tenants,
    update_tenant,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _get_session(request: Request) -> AsyncSession:
    session: Optional[AsyncSession] = getattr(request.app.state, "db_session_factory", None)
    if session is None:
        raise RuntimeError("app.state.db_session_factory not configured")
    return session()


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create(body: TenantCreate, request: Request) -> TenantResponse:
    async with _get_session(request) as session:
        async with session.begin():
            try:
                tenant = await create_tenant(session, body)
            except TenantNameConflictError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return TenantResponse.model_validate(tenant)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def read_one(tenant_id: uuid.UUID, request: Request) -> TenantResponse:
    async with _get_session(request) as session:
        try:
            tenant = await get_tenant(session, tenant_id)
        except TenantNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return TenantResponse.model_validate(tenant)


@router.get("", response_model=list[TenantResponse])
async def read_many(
    request: Request,
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[TenantResponse]:
    async with _get_session(request) as session:
        tenants = await list_tenants(session, is_active=is_active, limit=limit, offset=offset)
    return [TenantResponse.model_validate(t) for t in tenants]


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def patch(tenant_id: uuid.UUID, body: TenantUpdate, request: Request) -> TenantResponse:
    async with _get_session(request) as session:
        async with session.begin():
            try:
                tenant = await update_tenant(session, tenant_id, body)
            except TenantNotFoundError as exc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
            except TenantNameConflictError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return TenantResponse.model_validate(tenant)


@router.delete("/{tenant_id}", response_model=TenantResponse)
async def deactivate(tenant_id: uuid.UUID, request: Request) -> TenantResponse:
    async with _get_session(request) as session:
        async with session.begin():
            try:
                tenant = await deactivate_tenant(session, tenant_id)
            except TenantNotFoundError as exc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return TenantResponse.model_validate(tenant)
