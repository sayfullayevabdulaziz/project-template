import argparse
import asyncio
import getpass
import sys

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.repository import RefreshTokenRepository
from app.core.config import get_settings
from app.core.db import make_engine, make_session_factory
from app.users.models import Role, User
from app.users.repository import UserRepository
from app.users.schemas import Email
from app.users.service import UserService

MIN_PASSWORD_LENGTH = 12


async def create_admin(
    session_factory: async_sessionmaker[AsyncSession], email: str, password: str
) -> User:
    async with session_factory() as session:
        svc = UserService(UserRepository(session), RefreshTokenRepository(session))
        user = await svc.get_by_email(email)
        if user is None:
            user = await svc.register(email, password, role=Role.admin)
            print(f"created admin {user.email}")
        elif user.role == Role.admin:
            print(f"{user.email} is already an admin")
        else:
            # promotion keeps the existing password; the supplied one is ignored
            await svc.promote_to_admin(user)
            print(f"promoted {user.email} to admin")
        await session.commit()
        return user


def _read_password() -> str:
    password = getpass.getpass("Password: ")
    if getpass.getpass("Repeat password: ") != password:
        raise ValueError("passwords do not match")
    return password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="create-admin", description="Create or promote an admin.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help="min 12 chars; prompted (hidden) when omitted")
    args = parser.parse_args(argv)

    try:
        email = TypeAdapter(Email).validate_python(args.email)
        password = args.password if args.password is not None else _read_password()
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    except ValidationError:
        print(f"error: invalid email: {args.email}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    async def run() -> None:
        engine = make_engine(get_settings().database_url)
        try:
            await create_admin(make_session_factory(engine), email, password)
        finally:
            await engine.dispose()

    asyncio.run(run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
