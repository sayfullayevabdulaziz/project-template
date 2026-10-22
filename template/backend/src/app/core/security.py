import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TypedDict
from uuid import UUID

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.errors import Unauthorized

_hasher = PasswordHash.recommended()

# Precomputed so login can verify against it for unknown users and equalize timing.
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$eNDG4QncnORpvhxtJk22Iw$A3b2OPU7vR0DsQF/w14SBYqRYfXFPMKhfelQUK4BC+Y"  # noqa: E501


class AccessClaims(TypedDict):
    sub: UUID
    role: str


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(password, hashed)
    except UnknownHashError:
        return False


def create_access_token(
    user_id: UUID,
    role: str,
    secret: str,
    *,
    now: datetime | None = None,
    ttl: timedelta = timedelta(minutes=15),
) -> str:
    now = now or datetime.now(UTC)
    payload = {"sub": str(user_id), "role": role, "type": "access", "iat": now, "exp": now + ttl}
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, secret: str) -> AccessClaims:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
        if payload["type"] != "access" or not isinstance(payload.get("role"), str):
            raise Unauthorized("Invalid token")
        return {"sub": UUID(payload["sub"]), "role": payload["role"]}
    except (jwt.PyJWTError, ValueError, TypeError, AttributeError) as exc:
        raise Unauthorized("Invalid token") from exc


def new_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
