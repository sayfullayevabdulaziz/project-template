import getpass

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import cli
from app.auth.repository import RefreshTokenRepository
from app.core.security import verify_password
from app.users.models import Role
from app.users.repository import UserRepository
from app.users.service import UserService

PASSWORD = "correct horse battery"

type Factory = async_sessionmaker[AsyncSession]


async def test_create_admin_creates_admin_user(committed_session_factory: Factory) -> None:
    user = await cli.create_admin(committed_session_factory, "Root@Example.COM", PASSWORD)

    assert user.role == Role.admin
    assert user.email == "root@example.com"
    assert verify_password(PASSWORD, user.password_hash)
    async with committed_session_factory() as s:
        stored = await UserRepository(s).get_by_email("root@example.com")
    assert stored is not None
    assert stored.role == Role.admin


async def test_create_admin_idempotent(
    committed_session_factory: Factory, capsys: pytest.CaptureFixture[str]
) -> None:
    first = await cli.create_admin(committed_session_factory, "root@example.com", PASSWORD)
    second = await cli.create_admin(
        committed_session_factory, "root@example.com", "another password!"
    )

    assert second.id == first.id
    assert "already an admin" in capsys.readouterr().out
    assert verify_password(PASSWORD, second.password_hash)  # existing password untouched


async def test_create_admin_promotes_existing_user(committed_session_factory: Factory) -> None:
    async with committed_session_factory() as s:
        await UserService(UserRepository(s), RefreshTokenRepository(s)).register(
            "user@example.com", PASSWORD
        )
        await s.commit()

    user = await cli.create_admin(committed_session_factory, "USER@example.com", "x" * 12)

    assert user.role == Role.admin
    async with committed_session_factory() as s:
        stored = await UserRepository(s).get_by_email("user@example.com")
    assert stored is not None
    assert stored.role == Role.admin
    assert verify_password(PASSWORD, stored.password_hash)  # promotion keeps the password


def test_main_rejects_short_password(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--email", "root@example.com", "--password", "short"]) == 1
    assert "12" in capsys.readouterr().err


def test_main_rejects_invalid_email(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--email", "not-an-email", "--password", PASSWORD]) == 1
    assert "email" in capsys.readouterr().err.lower()


def test_main_prompt_mismatch_and_short(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter([PASSWORD, "different password"])
    monkeypatch.setattr(getpass, "getpass", lambda _prompt="": next(answers))
    assert cli.main(["--email", "root@example.com"]) == 1
    assert "match" in capsys.readouterr().err

    monkeypatch.setattr(getpass, "getpass", lambda _prompt="": "short")
    assert cli.main(["--email", "root@example.com"]) == 1
    assert "12" in capsys.readouterr().err
