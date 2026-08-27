from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.tutor import TutorChatRequest, TutorChatResponse
from app.services.auth_service import get_current_user
from app.services.tutor_service import TutorService

router = APIRouter(prefix="/tutor", tags=["AI Tutor"])


@router.post("/chat", response_model=ApiResponse[TutorChatResponse])
async def tutor_chat(
    payload: TutorChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TutorService(db)
    response = await service.chat(user_id=current_user.id, payload=payload)
    return ApiResponse(data=response)
