from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken
from app.core.errors import Conflict, NotFound
from app.core.pagination import ListParams, apply_sort, escape_like
from app.core.security import hash_password
from app.users.models import Role, User


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email.lower()))


async def get(session: AsyncSession, user_id: UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFound("User not found")
    return user


async def register(
    session: AsyncSession, email: str, password: str, role: Role = Role.user
) -> User:
    email = email.lower()
    if await get_by_email(session, email) is not None:
        raise Conflict("Email already registered")
    user = User(email=email, password_hash=hash_password(password), role=role)
    try:
        # savepoint: a lost race must not poison the caller's transaction
        async with session.begin_nested():
            session.add(user)
            await session.flush()
    except IntegrityError as exc:
        raise Conflict("Email already registered") from exc
    return user


async def list_users(session: AsyncSession, params: ListParams) -> tuple[list[User], int]:
    where = []
    if params.q:
        where.append(User.email.ilike(f"%{escape_like(params.q.lower())}%", escape="\\"))
    total = await session.scalar(select(func.count()).select_from(User).where(*where))
    stmt = apply_sort(select(User).where(*where), User, params.sort)
    rows = await session.scalars(stmt.limit(params.limit).offset(params.offset))
    return list(rows), total or 0


async def admin_update(
    session: AsyncSession, actor: User, user_id: UUID, role: Role | None, is_active: bool | None
) -> User:
    target = await session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if target is None:
        raise NotFound("User not found")

    demotes = target.role == Role.admin and role == Role.user
    deactivates = target.is_active and is_active is False
    if target.role == Role.admin and target.is_active and (demotes or deactivates):
        if target.id == actor.id:
            raise Conflict("cannot demote or deactivate yourself")
        other_active_admins = await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == Role.admin, User.is_active, User.id != target.id)
        )
        if not other_active_admins:
            raise Conflict("cannot remove the last active admin")

    if role is not None:
        target.role = role
    if is_active is not None:
        target.is_active = is_active
    if deactivates:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == target.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )
    await session.flush()
    return target
