
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.search import AskKnowledgeRequest, AskKnowledgeResponse, SearchResultItem
from app.services.auth_service import get_current_user
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Semantic Search & RAG"])


@router.get("", response_model=ApiResponse[list[SearchResultItem]])
async def semantic_search(
    q: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SearchService(db)
    results = await service.search(user_id=current_user.id, query=q, limit=limit)
    return ApiResponse(data=results)


@router.post("/ask", response_model=ApiResponse[AskKnowledgeResponse])
async def ask_my_knowledge(
    payload: AskKnowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SearchService(db)
    response = await service.ask_my_knowledge(user_id=current_user.id, payload=payload)
    return ApiResponse(data=response)
