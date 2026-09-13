from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.model_registry import ModelDefinition, ModelInstance
from app.models.permission import UserModelPermission
from app.models.user import User
from app.providers.base import InferenceProvider
from app.providers.registry import provider_registry
from app.router.classifier import request_classifier
from app.router.load_balancer import load_balancer
from app.schemas.openai import ChatCompletionRequest


class RouterEngine:
    """
    Universal Model Router:
    - Zero-LLM Request Classification for 'universal' / 'auto' / 'smart'
    - Exact slug matching & universal alias resolution
    - Capability negotiation and memory-aware bounds
    - Prepares primary provider and secondary fallback chain
    """

    @classmethod
    async def resolve_model(
        cls,
        requested_model: str,
        user: User,
        db: AsyncSession,
        request: Optional[ChatCompletionRequest] = None,
    ) -> Tuple[ModelDefinition, Optional[ModelInstance], InferenceProvider]:
        primary_model, primary_instance, primary_provider, _ = await cls.resolve_model_candidates(
            requested_model=requested_model,
            user=user,
            db=db,
            request=request,
        )
        return primary_model, primary_instance, primary_provider

    @classmethod
    async def resolve_model_candidates(
        cls,
        requested_model: str,
        user: User,
        db: AsyncSession,
        request: Optional[ChatCompletionRequest] = None,
    ) -> Tuple[
        ModelDefinition,
        Optional[ModelInstance],
        InferenceProvider,
        List[Tuple[ModelDefinition, Optional[ModelInstance], InferenceProvider]],
    ]:
        req_clean = requested_model.strip().lower()

        # Fetch all registered models
        stmt = select(ModelDefinition).options(selectinload(ModelDefinition.instances))
        res = await db.execute(stmt)
        all_models = res.scalars().all()
        enabled_models = [m for m in all_models if m.enabled and m.backend != "router"]

        matched_model: Optional[ModelDefinition] = None

        # 1. Smart Universal / Auto Routing Mode
        if req_clean in ("universal", "auto", "smart") and request is not None:
            target_cap = request_classifier.classify_request(request)
            logger.info(f"Universal Router classified request target capability as: '{target_cap}'")

            # Filter candidates by capability
            candidates = cls._filter_by_capability(enabled_models, target_cap)
            if candidates:
                candidates.sort(key=lambda m: m.priority, reverse=True)
                matched_model = candidates[0]

        # 2. Universal Alias Matching (fast, coding, reasoning, vision, embedding, etc.)
        if not matched_model:
            for m in all_models:
                if m.slug.lower() == req_clean:
                    matched_model = m
                    break

        if not matched_model:
            for m in all_models:
                if m.aliases:
                    alias_list = [a.strip().lower() for a in m.aliases.split(",")]
                    if req_clean in alias_list:
                        matched_model = m
                        break

        # Fallback to any enabled model if universal router found no capability match
        if not matched_model and req_clean in ("universal", "auto", "smart"):
            sorted_enabled = sorted(enabled_models, key=lambda m: m.priority, reverse=True)
            if sorted_enabled:
                matched_model = sorted_enabled[0]

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

        # Primary instance selection
        primary_instance = load_balancer.select_instance(matched_model)
        primary_endpoint = primary_instance.endpoint if primary_instance else matched_model.endpoint
        primary_provider = provider_registry.get_provider(
            backend=matched_model.backend,
            endpoint=primary_endpoint,
            model_name=matched_model.backend_model_name,
        )

        # Build secondary fallback candidates (excluding primary matched_model)
        fallback_candidates: List[Tuple[ModelDefinition, Optional[ModelInstance], InferenceProvider]] = []
        other_enabled = [m for m in enabled_models if m.id != matched_model.id]
        other_enabled.sort(key=lambda m: m.priority, reverse=True)

        for fallback_m in other_enabled:
            fb_inst = load_balancer.select_instance(fallback_m)
            fb_endpoint = fb_inst.endpoint if fb_inst else fallback_m.endpoint
            fb_provider = provider_registry.get_provider(
                backend=fallback_m.backend,
                endpoint=fb_endpoint,
                model_name=fallback_m.backend_model_name,
            )
            fallback_candidates.append((fallback_m, fb_inst, fb_provider))

        return matched_model, primary_instance, primary_provider, fallback_candidates

    @staticmethod
    def _filter_by_capability(models: List[ModelDefinition], capability: str) -> List[ModelDefinition]:
        res: List[ModelDefinition] = []
        for m in models:
            if capability == "vision" and m.supports_vision:
                res.append(m)
            elif capability == "coding" and (m.supports_coding or "coder" in m.slug or "coding" in (m.aliases or "")):
                res.append(m)
            elif capability == "reasoning" and (m.supports_reasoning or "reasoning" in m.slug or "27b" in m.slug):
                res.append(m)
            elif capability == "fast" and ("fast" in m.slug or "fast" in (m.aliases or "") or m.priority >= 90):
                res.append(m)
        return res if res else models


router_engine = RouterEngine()
