"""
FastAPI dependencies: authentication, rate limiting, database session.
"""

from __future__ import annotations

import time
import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import Role, TokenPayload, check_permission, decode_access_token
from app.db.session import get_db

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)

# In-memory rate limiting (replace with Redis in production cluster)
_rate_limits: dict[str, list[float]] = {}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TokenPayload:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication")
    try:
        return decode_access_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


def require_permission(permission: str):
    """Dependency factory: require a specific permission."""

    async def _check(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if not check_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return user

    return _check


def require_role(*roles: Role):
    """Dependency factory: require one of the given roles."""

    async def _check(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {', '.join(r.value for r in roles)}",
            )
        return user

    return _check


async def rate_limit(request: Request, user: TokenPayload = Depends(get_current_user)) -> None:
    """Simple sliding-window rate limiter."""
    key = user.sub
    now = time.time()
    window = 60.0

    timestamps = _rate_limits.setdefault(key, [])
    # Purge old entries
    _rate_limits[key] = [t for t in timestamps if now - t < window]

    if len(_rate_limits[key]) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again shortly.",
        )

    _rate_limits[key].append(now)
