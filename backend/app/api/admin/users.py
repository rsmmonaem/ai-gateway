from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.token import get_current_admin
from app.core.security import get_password_hash
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/admin/users", tags=["Admin - Users"])


@router.get("", response_model=List[UserOut])
async def list_users(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all registered users."""
    res = await db.execute(select(User).order_by(User.id.asc()))
    return res.scalars().all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user account."""
    res = await db.execute(select(User).where(User.email == user_in.email))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    new_user = User(
        email=user_in.email,
        name=user_in.name,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role,
        status="active",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user attributes (status, role, password)."""
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_dict = user_update.model_dump(exclude_unset=True)
    if "password" in update_dict and update_dict["password"]:
        user.password_hash = get_password_hash(update_dict.pop("password"))

    for k, v in update_dict.items():
        setattr(user, k, v)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user account and associated API keys."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
