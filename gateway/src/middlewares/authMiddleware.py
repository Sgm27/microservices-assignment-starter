"""JWT decoding helper (not a FastAPI middleware class — a plain function used by routes)."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from ..config.settings import get_settings


def extract_token(request: Request) -> Optional[str]:
    header = request.headers.get("authorization")
    if not header:
        return None
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def decode_claims(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc


def require_auth(request: Request) -> dict:
    token = extract_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    return decode_claims(token)


def optional_auth(request: Request) -> Optional[dict]:
    token = extract_token(request)
    if not token:
        return None
    try:
        return decode_claims(token)
    except HTTPException:
        return None
