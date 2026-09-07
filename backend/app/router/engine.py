from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.model_registry import ModelDefinition, ModelInstance
from app.models.permission import UserModelPermission
from app.models.user import User
from app.providers.base import InferenceProvider
from app.providers.registry import provider_registry
from app.router.load_balancer import load_balancer


class RouterEngine:
    """
    Core Model Router:
    - Resolves exact model slugs, aliases, and 'auto' routing
    - Validates user permissions
    - Dispatches to healthiest instance
    - Prepares the concrete InferenceProvider
    """

    @staticmethod
    async def resolve_model(
        requested_model: str,
        user: User,
        db: AsyncSession,
    ) -> Tuple[ModelDefinition, Optional[ModelInstance], InferenceProvider]:
        req_clean = requested_model.strip()

        # Eager load instances
        stmt = select(ModelDefinition).options(selectinload(ModelDefinition.instances))
        res = await db.execute(stmt)
        all_models = res.scalars().all()

        matched_model: Optional[ModelDefinition] = None

        if req_clean.lower() == "auto":
            # Auto-routing: choose highest-priority enabled model
            enabled = [m for m in all_models if m.enabled]
            if enabled:
                enabled.sort(key=lambda m: m.priority, reverse=True)
                matched_model = enabled[0]
        else:
            # 1. Exact slug match
            for m in all_models:
                if m.slug.lower() == req_clean.lower():
                    matched_model = m
                    break

            # 2. Alias match
            if not matched_model:
                for m in all_models:
                    if m.aliases:
                        alias_list = [a.strip().lower() for a in m.aliases.split(",")]
                        if req_clean.lower() in alias_list:
                            matched_model = m
                            break

        if not matched_model or not matched_model.enabled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "message": f"The model '{requested_model}' does not exist or is disabled.",
                        "type": "invalid_request_error",
                        "param": "model",
                        "code": "model_not_found",
                    }
                },
            )

        # Check User Model Permissions (Admin bypasses restrictions)
        if user.role != "admin":
            perm_stmt = select(UserModelPermission).where(
                UserModelPermission.user_id == user.id,
                UserModelPermission.model_id == matched_model.id,
            )
            perm_res = await db.execute(perm_stmt)
            perm = perm_res.scalar_one_or_none()
            if perm is not None and not perm.allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": {
                            "message": f"You do not have permission to access model '{matched_model.slug}'.",
                            "type": "access_denied",
                            "param": "model",
                            "code": "model_permission_denied",
                        }
                    },
                )

        # Select instance via Load Balancer
        instance = load_balancer.select_instance(matched_model)
        target_endpoint = instance.endpoint if instance else matched_model.endpoint

        # Instantiate provider
        provider = provider_registry.get_provider(
            backend=matched_model.backend,
            endpoint=target_endpoint,
            model_name=matched_model.backend_model_name,
        )

        return matched_model, instance, provider


router_engine = RouterEngine()
