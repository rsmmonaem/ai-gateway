from datetime import timezone
from typing import List, Tuple
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
    List all available models and universal aliases.
    Compatible with OpenAI's GET /v1/models.
    """
    user, _ = auth

    stmt = select(ModelDefinition).where(ModelDefinition.enabled == True)
    res = await db.execute(stmt)
    all_models = res.scalars().all()

    permitted_models: List[ModelDefinition] = []
    if user.role == "admin":
        permitted_models = all_models
    else:
        perm_stmt = select(UserModelPermission).where(UserModelPermission.user_id == user.id)
        perm_res = await db.execute(perm_stmt)
        perms = {p.model_id: p.allowed for p in perm_res.scalars().all()}

        for m in all_models:
            if perms.get(m.id, True):
                permitted_models.append(m)

    data: List[ModelObject] = []
    for m in permitted_models:
        created_ts = int(m.created_at.replace(tzinfo=timezone.utc).timestamp()) if m.created_at else 1700000000
        # Add primary slug
        data.append(
            ModelObject(
                id=m.slug,
                created=created_ts,
                owned_by=m.provider,
                context_length=m.context_length,
                description=m.description,
            )
        )
        # Expose individual aliases if present
        if m.aliases:
            for alias in m.aliases.split(","):
                alias_clean = alias.strip()
                if alias_clean and alias_clean != m.slug and not any(d.id == alias_clean for d in data):
                    data.append(
                        ModelObject(
                            id=alias_clean,
                            created=created_ts,
                            owned_by=m.provider,
                            context_length=m.context_length,
                            description=f"Alias for {m.name}",
                        )
                    )

    return ModelListResponse(data=data)


@router.get("/{model_id}", response_model=ModelObject)
async def get_model(
    model_id: str,
    auth: Tuple[User, APIKey] = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific model or alias."""
    model_id_clean = model_id.strip().lower()
    stmt = select(ModelDefinition).where(ModelDefinition.enabled == True)
    res = await db.execute(stmt)
    all_models = res.scalars().all()

    matched: Optional[ModelDefinition] = None
    for m in all_models:
        if m.slug.lower() == model_id_clean:
            matched = m
            break
        if m.aliases:
            aliases = [a.strip().lower() for a in m.aliases.split(",")]
            if model_id_clean in aliases:
                matched = m
                break

    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"message": f"Model '{model_id}' not found", "code": "model_not_found"}},
        )

    created_ts = int(matched.created_at.replace(tzinfo=timezone.utc).timestamp()) if matched.created_at else 1700000000
    return ModelObject(
        id=model_id_clean,
        created=created_ts,
        owned_by=matched.provider,
        context_length=matched.context_length,
        description=matched.description,
    )
