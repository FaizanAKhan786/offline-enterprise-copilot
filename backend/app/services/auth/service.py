"""
Authentication service: user CRUD, login, token management.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import Role, create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas.schemas import TokenResponse, UserCreate, UserResponse

logger = get_logger(__name__)
settings = get_settings()


class AuthService:
    """Handles user authentication and management."""

    async def login(self, db: AsyncSession, email: str, password: str) -> TokenResponse:
        user = await self._get_user_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is disabled")

        token = create_access_token(str(user.id), user.role)
        logger.info("User logged in", user_id=str(user.id), role=user.role)
        return TokenResponse(
            access_token=token,
            expires_in=settings.jwt_expiry_minutes * 60,
            role=user.role,
        )

    async def create_user(self, db: AsyncSession, data: UserCreate) -> UserResponse:
        existing = await self._get_user_by_email(db, data.email)
        if existing:
            raise ValueError("Email already registered")

        user = User(
            id=uuid.uuid4(),
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info("User created", user_id=str(user.id), role=data.role)
        return UserResponse.model_validate(user)

    async def get_user(self, db: AsyncSession, user_id: uuid.UUID) -> UserResponse | None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return UserResponse.model_validate(user) if user else None

    async def ensure_default_admin(self, db: AsyncSession) -> None:
        """Create the default admin user if none exists."""
        result = await db.execute(select(User).where(User.role == Role.ADMIN).limit(1))
        if result.scalar_one_or_none():
            return

        admin = User(
            id=uuid.uuid4(),
            email=settings.default_admin_email,
            hashed_password=hash_password(settings.default_admin_password),
            full_name="System Administrator",
            role=Role.ADMIN,
        )
        db.add(admin)
        await db.commit()
        logger.info("Default admin created", email=settings.default_admin_email)

    async def _get_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


auth_service = AuthService()
