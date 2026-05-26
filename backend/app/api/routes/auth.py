"""
Authentication routes: login, register, user management.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.security import Role, TokenPayload
from app.db.session import get_db
from app.schemas.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services.auth.service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await auth_service.login(db, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: TokenPayload = Depends(require_role(Role.ADMIN)),
):
    """Create a new user (admin only)."""
    try:
        return await auth_service.create_user(db, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    import uuid as _uuid
    result = await auth_service.get_user(db, _uuid.UUID(user.sub))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result
