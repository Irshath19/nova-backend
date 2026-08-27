from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.progress import ProgressMetricsOut
from app.services.auth_service import get_current_user
from app.services.progress_service import ProgressService

router = APIRouter(prefix="/progress", tags=["Knowledge Progress"])


@router.get("", response_model=ApiResponse[ProgressMetricsOut])
async def get_progress_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProgressService(db)
    metrics = await service.get_metrics(user_id=current_user.id)
    return ApiResponse(data=metrics)
