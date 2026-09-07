from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.token import get_current_user
from app.core.security import create_access_token, verify_password
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password to receive a JWT session token."""
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled.",
        )

    token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        email=user.email,
        name=user.name,
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get profile information for the authenticated session user."""
    return current_user
