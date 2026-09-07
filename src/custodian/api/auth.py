"""Authentication and Authorization module for Custodian API.

Implements Local OAuth2 with JWT tokens and Argon2id password hashing.
Zero cloud telemetry, air-gapped capable.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from custodian.storage.sqlite import SQLiteRepository

# Key settings
JWT_SECRET = os.getenv(
    "CUSTODIAN_JWT_SECRET", "custodian_local_jwt_secret_key_2026_safe_32bytes_min"
)
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

ph = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class UserResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    role: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user_id: str, username: str, role: str) -> str:
    expires = datetime.now(UTC) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expires,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


DEMO_USERS = [
    {
        "user_id": "usr_admin_001",
        "username": "admin",
        "display_name": "Lead Security Administrator",
        "password": "CustodianAdmin2026!",
        "role": "Admin",
    },
    {
        "user_id": "usr_analyst_002",
        "username": "analyst",
        "display_name": "Threat Incident Analyst",
        "password": "CustodianAnalyst2026!",
        "role": "Analyst",
    },
    {
        "user_id": "usr_auditor_003",
        "username": "auditor",
        "display_name": "Compliance & Forensics Auditor",
        "password": "CustodianAuditor2026!",
        "role": "Auditor",
    },
]


def seed_demo_users_if_needed(repo: SQLiteRepository) -> None:
    """Seed initial demo accounts for presentation if no users exist."""
    existing = repo.list_users()
    if not existing:
        for u in DEMO_USERS:
            pw_hash = hash_password(u["password"])
            repo.upsert_user(
                user_id=u["user_id"],
                username=u["username"],
                display_name=u["display_name"],
                password_hash=pw_hash,
                role=u["role"],
            )


def get_current_user_from_raw_token(token: str, repo: SQLiteRepository) -> dict:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User account no longer exists"
        )
    return user
