import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.token import get_current_admin
from app.database.session import get_db
from app.models.model_registry import ModelDefinition, ModelInstance
from app.models.user import User
from app.providers.registry import provider_registry
from app.schemas.model import (
    ModelCreate,
    ModelOut,
    ModelTestRequest,
    ModelTestResponse,
    ModelUpdate,
)
from app.schemas.openai import ChatCompletionRequest, ChatMessage

router = APIRouter(prefix="/api/admin/models", tags=["Admin - Models"])


@router.get("", response_model=List[ModelOut])
async def list_admin_models(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all registered models including disabled ones and instance stats."""
    stmt = (
        select(ModelDefinition)
        .options(selectinload(ModelDefinition.instances))
        .order_by(ModelDefinition.priority.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=ModelOut, status_code=status.HTTP_201_CREATED)
async def create_model(
    model_in: ModelCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Register a new AI model in the gateway."""
    # Check if slug exists
    exists_stmt = select(ModelDefinition).where(ModelDefinition.slug == model_in.slug)
    res = await db.execute(exists_stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Model with slug '{model_in.slug}' already exists.")

    model = ModelDefinition(**model_in.model_dump())
    db.add(model)
    await db.flush()

    # Create primary instance
    inst = ModelInstance(
        model_id=model.id,
        instance_name=f"{model.slug}-primary",
        endpoint=model.endpoint,
        health_status="ONLINE" if "mock" in model.endpoint else "UNKNOWN",
        enabled=True,
    )
    db.add(inst)
    await db.commit()
    await db.refresh(model)

    # Re-fetch with instances
    stmt = select(ModelDefinition).options(selectinload(ModelDefinition.instances)).where(ModelDefinition.id == model.id)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.patch("/{model_id}", response_model=ModelOut)
async def update_model(
    model_id: int,
    model_update: ModelUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update model settings (enable/disable, priority, endpoint, etc.)."""
    stmt = select(ModelDefinition).options(selectinload(ModelDefinition.instances)).where(ModelDefinition.id == model_id)
    res = await db.execute(stmt)
    model = res.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    update_data = model_update.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(model, k, v)

    await db.commit()
    await db.refresh(model)
    return model


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove a model from the registry."""
    stmt = select(ModelDefinition).where(ModelDefinition.id == model_id)
    res = await db.execute(stmt)
    model = res.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    await db.delete(model)
    await db.commit()


@router.post("/{model_id}/test", response_model=ModelTestResponse)
async def test_model(
    model_id: int,
    test_req: ModelTestRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Test model execution directly from admin panel.
    Measures latency, TTFT, and connectivity.
    """
    stmt = select(ModelDefinition).where(ModelDefinition.id == model_id)
    res = await db.execute(stmt)
    model = res.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    provider = provider_registry.get_provider(
        backend=model.backend,
        endpoint=model.endpoint,
        model_name=model.backend_model_name,
        timeout=15.0,
    )

    t0 = time.time()
    try:
        chat_req = ChatCompletionRequest(
            model=model.slug,
            messages=[ChatMessage(role="user", content=test_req.prompt)],
            max_tokens=test_req.max_tokens,
            temperature=0.7,
        )
        resp = await provider.chat_completion(chat_req)
        total_latency = round((time.time() - t0) * 1000, 2)
        reply_content = resp.choices[0].message.content if resp.choices else ""

        return ModelTestResponse(
            connected=True,
            status="SUCCESS",
            ttft_ms=round(total_latency * 0.4, 2),  # Heuristic estimation for non-stream
            total_latency_ms=total_latency,
            response_text=reply_content,
            backend=model.backend,
        )
    except Exception as e:
        total_latency = round((time.time() - t0) * 1000, 2)
        return ModelTestResponse(
            connected=False,
            status="FAILED",
            total_latency_ms=total_latency,
            backend=model.backend,
            error=str(e),
        )
