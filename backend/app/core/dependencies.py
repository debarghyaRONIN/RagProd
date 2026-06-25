import uuid
from typing import AsyncGenerator
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import async_session_maker
from app.config import settings
from app.core.auth import decode_access_token
from app.core.exceptions import CredentialsException, ForbiddenException, NotFoundException
from app.models.user import User

# Standard OAuth2 scheme for Swagger UI or API clients
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for async PostgreSQL sessions."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_token_from_request(
    request: Request,
    header_token: str | None = Depends(oauth2_scheme)
) -> str:
    """
    Extract token from either:
    1. HTTP Authorization Header (Bearer token)
    2. HTTP Cookie (access_token)
    """
    if header_token:
        return header_token

    # Check cookies as well
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        # If cookie has "Bearer <token>" prefix, clean it up
        if cookie_token.startswith("Bearer "):
            return cookie_token.split(" ")[1]
        return cookie_token

    raise CredentialsException("Authentication token is missing")

async def get_current_user(
    token: str = Depends(get_token_from_request),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Retrieve the current authenticated user or raise CredentialsException."""
    payload = decode_access_token(token)
    if not payload:
        raise CredentialsException("Invalid or expired token")
    
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise CredentialsException("Token lacks subject identifier")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise CredentialsException("Malformed subject identifier in token")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalars().first()
    
    if not user:
        raise NotFoundException("User associated with this token was not found")
        
    if not user.is_active:
        raise ForbiddenException("User account is inactive")
        
    return user
