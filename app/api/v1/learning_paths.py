
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.learning_path import (
    GeneratedLearningPathResponse,
    LearningPathCreate,
    LearningPathItemUpdate,
    LearningPathOut,
    LearningPathUpdate,
)

from app.services.auth_service import get_current_user
from app.services.learning_path_service import LearningPathService

router = APIRouter(prefix="/learning-paths", tags=["Learning Paths"])


class GeneratePathPayload(BaseModel):
    topic: str


@router.get("", response_model=ApiResponse[list[LearningPathOut]])
async def list_paths(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LearningPathService(db)
    paths = await service.list_paths(user_id=current_user.id)
    return ApiResponse(data=paths)


@router.post("", response_model=ApiResponse[LearningPathOut], status_code=status.HTTP_201_CREATED)
async def create_path(
    payload: LearningPathCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LearningPathService(db)
    path = await service.create_path(user_id=current_user.id, payload=payload)
    return ApiResponse(data=path)


@router.post("/generate", response_model=ApiResponse[GeneratedLearningPathResponse])
async def generate_path(
    payload: GeneratePathPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LearningPathService(db)
    generated = await service.generate_with_ai(user_id=current_user.id, topic=payload.topic)
    return ApiResponse(data=generated)


@router.get("/{path_id}", response_model=ApiResponse[LearningPathOut])
async def get_path(
    path_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LearningPathService(db)
    path = await service.get_path(path_id=path_id, user_id=current_user.id)
    return ApiResponse(data=path)


@router.put("/{path_id}", response_model=ApiResponse[LearningPathOut])
async def update_path(
    path_id: str,
    payload: LearningPathUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LearningPathService(db)
    path = await service.update_path(path_id=path_id, user_id=current_user.id, payload=payload)
    return ApiResponse(data=path)



@router.put("/{path_id}/items/{item_id}", response_model=ApiResponse[LearningPathOut])
async def update_path_item(
    path_id: str,
    item_id: str,
    payload: LearningPathItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LearningPathService(db)
    path = await service.update_item_status(
        path_id=path_id, item_id=item_id, user_id=current_user.id, payload=payload
    )
    return ApiResponse(data=path)


@router.delete("/{path_id}", response_model=ApiResponse[dict])
async def delete_path(
    path_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LearningPathService(db)
    await service.delete_path(path_id=path_id, user_id=current_user.id)
    return ApiResponse(data={"message": "Learning path deleted successfully"})
