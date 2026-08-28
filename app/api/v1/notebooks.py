from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.notebook import NotebookCreate, NotebookOut
from app.services.auth_service import get_current_user
from app.services.notebook_service import NotebookService

router = APIRouter(prefix="/notebooks", tags=["Notebooks"])


@router.get("", response_model=ApiResponse[list[NotebookOut]])
async def list_notebooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotebookService(db)
    notebooks = await service.list_notebooks(user_id=current_user.id)
    return ApiResponse(data=[NotebookOut.model_validate(nb) for nb in notebooks])


@router.post("", response_model=ApiResponse[NotebookOut], status_code=status.HTTP_201_CREATED)
async def create_notebook(
    payload: NotebookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotebookService(db)
    notebook = await service.create_notebook(payload=payload, user_id=current_user.id)
    return ApiResponse(data=NotebookOut.model_validate(notebook))


@router.delete("/{notebook_id}", response_model=ApiResponse[dict])
async def delete_notebook(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotebookService(db)
    await service.delete_notebook(notebook_id=notebook_id, user_id=current_user.id)
    return ApiResponse(data={"message": "Notebook deleted successfully"})
