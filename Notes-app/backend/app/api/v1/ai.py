from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import (
    ExtractConceptsRequest,
    ExtractConceptsResponse,
    GenerateTagsRequest,
    GenerateTagsResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from app.schemas.common import ApiResponse
from app.schemas.learning_path import GeneratedLearningPathResponse
from app.services.ai.ollama import get_ai_provider
from app.services.auth_service import get_current_user
from app.services.learning_path_service import LearningPathService

router = APIRouter(prefix="/ai", tags=["AI Operations"])


@router.post("/summarize", response_model=ApiResponse[SummarizeResponse])
async def summarize(
    payload: SummarizeRequest,
    current_user: User = Depends(get_current_user),
):
    ai = get_ai_provider()
    res = await ai.summarize(payload.content)
    return ApiResponse(data=res)


@router.post("/extract-concepts", response_model=ApiResponse[ExtractConceptsResponse])
async def extract_concepts(
    payload: ExtractConceptsRequest,
    current_user: User = Depends(get_current_user),
):
    ai = get_ai_provider()
    concepts = await ai.extract_concepts(payload.content)
    return ApiResponse(data=ExtractConceptsResponse(concepts=concepts))


@router.post("/generate-tags", response_model=ApiResponse[GenerateTagsResponse])
async def generate_tags(
    payload: GenerateTagsRequest,
    current_user: User = Depends(get_current_user),
):
    ai = get_ai_provider()
    tags = await ai.generate_tags(payload.content)
    return ApiResponse(data=GenerateTagsResponse(tags=tags))


@router.post("/generate-learning-path", response_model=ApiResponse[GeneratedLearningPathResponse])
async def generate_learning_path(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    topic = payload.get("topic", "Computer Science")
    service = LearningPathService(db)
    generated = await service.generate_with_ai(user_id=current_user.id, topic=topic)
    return ApiResponse(data=generated)
