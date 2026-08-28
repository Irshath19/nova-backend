from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.note import NoteCreate, NoteListItem, NoteOut, NoteUpdate, QuickCaptureRequest
from app.services.auth_service import get_current_user
from app.services.note_service import NoteService

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("", response_model=ApiResponse[PaginatedResponse[NoteListItem]])
async def list_notes(
    tag_id: str | None = None,
    concept_id: str | None = None,
    notebook_id: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NoteService(db)
    notes, total = await service.list_notes(
        user_id=current_user.id,
        tag_id=tag_id,
        concept_id=concept_id,
        notebook_id=notebook_id,
        search=search,
        page=page,
        limit=limit,
    )
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    return ApiResponse(
        data=PaginatedResponse(
            items=[NoteListItem.model_validate(n) for n in notes],
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )
    )



@router.get("/notebooks", response_model=ApiResponse[list[str]])
async def list_notebooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NoteService(db)
    notebooks = await service.list_notebooks(user_id=current_user.id)
    return ApiResponse(data=notebooks)


@router.post("/quick-capture", response_model=ApiResponse[NoteOut], status_code=status.HTTP_201_CREATED)
async def quick_capture_note(
    payload: QuickCaptureRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NoteService(db)
    note = await service.quick_capture(
        payload=payload,
        user_id=current_user.id,
        background_tasks=background_tasks,
    )
    return ApiResponse(data=NoteOut.model_validate(note))


@router.post("", response_model=ApiResponse[NoteOut], status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NoteService(db)
    note = await service.create_note(
        payload=payload,
        user_id=current_user.id,
        background_tasks=background_tasks,
    )
    return ApiResponse(data=NoteOut.model_validate(note))


@router.get("/{note_id}", response_model=ApiResponse[NoteOut])
async def get_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    service = NoteService(db)
    note = await service.get_note(note_id=note_id, user_id=current_user.id)
    return ApiResponse(data=NoteOut.model_validate(note))


@router.put("/{note_id}", response_model=ApiResponse[NoteOut])
async def update_note(
    note_id: str,
    payload: NoteUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NoteService(db)
    note = await service.update_note(
        note_id=note_id,
        payload=payload,
        user_id=current_user.id,
        background_tasks=background_tasks,
    )
    return ApiResponse(data=NoteOut.model_validate(note))


@router.delete("/{note_id}", response_model=ApiResponse[dict])
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NoteService(db)
    await service.delete_note(note_id=note_id, user_id=current_user.id)
    return ApiResponse(data={"message": "Note deleted successfully"})
