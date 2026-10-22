import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.errors import Unauthorized
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)

SECRET = "s" * 32


def test_hash_roundtrip_and_argon2_prefix():
    hashed = hash_password("hunter2hunter2")
    assert hashed.startswith("$argon2")
    assert verify_password("hunter2hunter2", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("hunter2hunter2", "not-a-hash")
    assert not verify_password("anything", DUMMY_HASH)


def test_access_token_claims():
    uid = uuid4()
    token = create_access_token(uid, "admin", SECRET)
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert payload["type"] == "access"
    assert payload["exp"] - payload["iat"] == 900
    assert payload["role"] == "admin"
    assert payload["sub"] == str(uid)
    claims = decode_access_token(token, SECRET)
    assert claims["sub"] == uid
    assert claims["role"] == "admin"


def test_decode_rejects_expired():
    token = create_access_token(uuid4(), "user", SECRET, now=datetime.now(UTC) - timedelta(hours=2))
    with pytest.raises(Unauthorized):
        decode_access_token(token, SECRET)


def test_decode_rejects_refresh_type():
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "user",
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(Unauthorized):
        decode_access_token(token, SECRET)


def test_decode_rejects_alg_none():
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "user",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        None,
        algorithm="none",
    )
    with pytest.raises(Unauthorized):
        decode_access_token(token, SECRET)


def test_decode_rejects_wrong_secret():
    token = create_access_token(uuid4(), "user", SECRET)
    with pytest.raises(Unauthorized):
        decode_access_token(token, "x" * 32)


def test_decode_rejects_bad_sub():
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "not-a-uuid",
            "role": "user",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(Unauthorized):
        decode_access_token(token, SECRET)


@pytest.mark.parametrize("garbage", ["not.a.jwt", ""])
def test_decode_rejects_garbage(garbage: str):
    with pytest.raises(Unauthorized):
        decode_access_token(garbage, SECRET)


def test_refresh_token_unique_and_hash_is_sha256():
    a, b = new_refresh_token(), new_refresh_token()
    assert a != b
    h = hash_refresh_token(a)
    assert len(h) == 64
    int(h, 16)
    assert h != a
    assert h == hash_refresh_token(a)
    assert h == hashlib.sha256(a.encode()).hexdigest()
