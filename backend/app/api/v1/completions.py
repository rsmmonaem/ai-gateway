from typing import Tuple
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import get_api_key_auth
from app.database.session import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.router.engine import router_engine
from app.schemas.openai import CompletionRequest, CompletionResponse

router = APIRouter(prefix="/completions", tags=["OpenAI - Text Completions"])


@router.post("", response_model=CompletionResponse)
async def create_completion(
    req: CompletionRequest,
    auth: Tuple[User, APIKey] = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
):
    """Legacy OpenAI-compatible text completion endpoint."""
    user, _ = auth
    model_def, _, provider = await router_engine.resolve_model(
        requested_model=req.model, user=user, db=db
    )
    return await provider.completion(req)
