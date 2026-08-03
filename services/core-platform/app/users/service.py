from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User

from .schemas import UserCreate, UserUpdate


class UserNotFoundError(Exception):
    def __init__(self, user_id: uuid.UUID) -> None:
        super().__init__(f"User {user_id} not found")


class UserEmailConflictError(Exception):
    def __init__(self, email: str) -> None:
        super().__init__(f"Email already registered in this tenant: {email!r}")


async def create_user(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: UserCreate,
) -> User:
    existing = await session.scalar(
        select(User).where(
            and_(User.tenant_id == tenant_id, User.email == data.email)
        )
    )
    if existing is not None:
        raise UserEmailConflictError(data.email)

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=data.email,
        name=data.name,
        role=data.role,
        is_active=False,
        google_sub=data.google_sub,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def get_user(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> User:
    user = await session.scalar(
        select(User).where(
            and_(User.id == user_id, User.tenant_id == tenant_id)
        )
    )
    if user is None:
        raise UserNotFoundError(user_id)
    return user


async def list_users(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    is_active: Optional[bool] = None,
    role: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[User]:
    query = (
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if role is not None:
        query = query.where(User.role == role)
    result = await session.execute(query)
    return result.scalars().all()


async def update_user(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: UserUpdate,
) -> User:
    user = await get_user(session, tenant_id, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.flush()
    await session.refresh(user)
    return user


async def deactivate_user(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> User:
    user = await get_user(session, tenant_id, user_id)
    user.is_active = False
    await session.flush()
    await session.refresh(user)
    return user
