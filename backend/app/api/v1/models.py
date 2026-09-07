from datetime import timezone
from typing import Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import get_api_key_auth
from app.database.session import get_db
from app.models.api_key import APIKey
from app.models.model_registry import ModelDefinition
from app.models.permission import UserModelPermission
from app.models.user import User
from app.schemas.openai import ModelListResponse, ModelObject

router = APIRouter(prefix="/models", tags=["OpenAI - Models"])


@router.get("", response_model=ModelListResponse)
async def list_models(
    auth: Tuple[User, APIKey] = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    List all available models that the authenticated API key is permitted to call.
    Compatible with OpenAI's GET /v1/models.
    """
    user, _ = auth

    stmt = select(ModelDefinition).where(ModelDefinition.enabled == True)
    res = await db.execute(stmt)
    all_models = res.scalars().all()

    # Filter by user permissions if not admin
    permitted_models = []
    if user.role == "admin":
        permitted_models = all_models
    else:
        perm_stmt = select(UserModelPermission).where(UserModelPermission.user_id == user.id)
        perm_res = await db.execute(perm_stmt)
        perms = {p.model_id: p.allowed for p in perm_res.scalars().all()}

        for m in all_models:
            if perms.get(m.id, True):  # Default allow unless explicitly forbidden
                permitted_models.append(m)

    data = [
        ModelObject(
            id=m.slug,
            created=int(m.created_at.replace(tzinfo=timezone.utc).timestamp()),
            owned_by=m.provider,
            context_length=m.context_length,
            description=m.description,
        )
        for m in permitted_models
    ]

    return ModelListResponse(data=data)


@router.get("/{model_id}", response_model=ModelObject)
async def get_model(
    model_id: str,
    auth: Tuple[User, APIKey] = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific model."""
    stmt = select(ModelDefinition).where(
        ModelDefinition.slug == model_id, ModelDefinition.enabled == True
    )
    res = await db.execute(stmt)
    model = res.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"message": f"Model '{model_id}' not found", "code": "model_not_found"}},
        )

    return ModelObject(
        id=model.slug,
        created=int(model.created_at.replace(tzinfo=timezone.utc).timestamp()),
        owned_by=model.provider,
        context_length=model.context_length,
        description=model.description,
    )
