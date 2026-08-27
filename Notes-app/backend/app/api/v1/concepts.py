
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.concept import KnowledgeLevel
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.concept import ConceptCreate, ConceptDetailOut, ConceptOut, ConceptUpdate
from app.services.auth_service import get_current_user
from app.services.concept_service import ConceptService

router = APIRouter(prefix="/concepts", tags=["Concepts"])


@router.get("", response_model=ApiResponse[list[ConceptOut]])
async def list_concepts(
    knowledge_level: KnowledgeLevel | None = None,
    search: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConceptService(db)
    concepts = await service.list_concepts(
        user_id=current_user.id,
        knowledge_level=knowledge_level,
        search=search,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=[ConceptOut.model_validate(c) for c in concepts])


@router.post("", response_model=ApiResponse[ConceptOut], status_code=status.HTTP_201_CREATED)
async def create_concept(
    payload: ConceptCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConceptService(db)
    concept = await service.create_concept(payload=payload, user_id=current_user.id)
    return ApiResponse(data=ConceptOut.model_validate(concept))


@router.get("/{concept_id}", response_model=ApiResponse[ConceptDetailOut])
async def get_concept_detail(
    concept_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConceptService(db)
    detail = await service.get_concept_detail(concept_id=concept_id, user_id=current_user.id)
    return ApiResponse(data=detail)


@router.put("/{concept_id}", response_model=ApiResponse[ConceptOut])
async def update_concept(
    concept_id: str,
    payload: ConceptUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConceptService(db)
    concept = await service.update_concept(
        concept_id=concept_id, payload=payload, user_id=current_user.id
    )
    return ApiResponse(data=ConceptOut.model_validate(concept))


@router.delete("/{concept_id}", response_model=ApiResponse[dict])
async def delete_concept(
    concept_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConceptService(db)
    await service.delete_concept(concept_id=concept_id, user_id=current_user.id)
    return ApiResponse(data={"message": "Concept deleted successfully"})
