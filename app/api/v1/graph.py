from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.relationship import GraphResponse
from app.services.auth_service import get_current_user
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


@router.get("", response_model=ApiResponse[GraphResponse])
async def get_graph(
    limit: int = Query(150, ge=10, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = GraphService(db)
    graph_data = await service.get_graph(user_id=current_user.id, limit=limit)
    return ApiResponse(data=graph_data)


@router.get("/concept/{concept_id}", response_model=ApiResponse[GraphResponse])
async def get_concept_subgraph(
    concept_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = GraphService(db)
    graph_data = await service.get_graph(user_id=current_user.id, concept_id=concept_id)
    return ApiResponse(data=graph_data)
