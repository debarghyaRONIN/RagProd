from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.dependencies import get_db, get_current_user
from app.core.auth import hash_password, verify_password, create_access_token
from app.core.exceptions import BadRequestException, CredentialsException
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    # Check if email exists
    stmt_email = select(User).where(User.email == body.email)
    res_email = await db.execute(stmt_email)
    if res_email.scalars().first():
        raise BadRequestException("Email is already registered")

    # Check if username exists
    stmt_user = select(User).where(User.username == body.username)
    res_user = await db.execute(stmt_user)
    if res_user.scalars().first():
        raise BadRequestException("Username is already taken")

    # Create new user
    hashed_pw = hash_password(body.password)
    user = User(
        email=body.email,
        username=body.username,
        hashed_pw=hashed_pw
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(response: Response, body: UserLogin, db: AsyncSession = Depends(get_db)):
    """Log in an existing user and return a JWT access token + set Cookie."""
    # Query by username or email
    stmt = select(User).where(
        (User.email == body.username_or_email) | (User.username == body.username_or_email)
    )
    res = await db.execute(stmt)
    user = res.scalars().first()

    if not user or not verify_password(body.password, user.hashed_pw):
        raise CredentialsException("Incorrect username/email or password")

    if not user.is_active:
        raise BadRequestException("User account is disabled")

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    # Set httpOnly cookie for web security
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24, # 24 hours
        samesite="strict",
        secure=True # Set to False in non-HTTPS local dev if needed, but True is standard
    )

    return TokenResponse(access_token=access_token)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve details of the currently authenticated user."""
    return current_user

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    """Log out current user by clearing the JWT cookie."""
    response.delete_cookie(key="access_token")
    return {"detail": "Logged out successfully"}
