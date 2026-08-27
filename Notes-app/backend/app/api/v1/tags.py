
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.repositories.tag_repo import TagRepository
from app.schemas.common import ApiResponse
from app.schemas.tag import TagOut
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", response_model=ApiResponse[list[TagOut]])
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TagRepository(db)
    tags = await repo.list_by_user(user_id=current_user.id)
    return ApiResponse(data=[TagOut.model_validate(t) for t in tags])
