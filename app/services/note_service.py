import asyncio
import logging

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept
from app.models.note import Note, ProcessingStatus
from app.models.tag import Tag
from app.repositories.concept_repo import ConceptRepository
from app.repositories.note_repo import NoteRepository
from app.repositories.tag_repo import TagRepository
from app.schemas.note import NoteCreate, NoteUpdate, QuickCaptureRequest
from app.services.knowledge_pipeline import run_note_processing_pipeline

logger = logging.getLogger(__name__)


class NoteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.note_repo = NoteRepository(db)
        self.tag_repo = TagRepository(db)
        self.concept_repo = ConceptRepository(db)

    async def get_note(self, note_id: str, user_id: str) -> Note:
        note = await self.note_repo.get_by_id(note_id, user_id)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
        return note

    async def list_notes(
        self,
        user_id: str,
        tag_id: str | None = None,
        concept_id: str | None = None,
        notebook_id: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Note], int]:
        offset = (page - 1) * limit
        return await self.note_repo.list_by_user(
            user_id=user_id,
            tag_id=tag_id,
            concept_id=concept_id,
            notebook_id=notebook_id,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def quick_capture(
        self,
        payload: QuickCaptureRequest,
        user_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> Note:
        content = payload.content.strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        title = payload.title.strip() if payload.title else (lines[0][:60] if lines else "Quick Capture Note")

        note = await self.note_repo.create(
            user_id=user_id,
            title=title,
            content=content,
            source=payload.source,
            notebook_id=payload.notebook_id,
            processing_status=ProcessingStatus.PENDING,
        )
        await self.db.commit()

        # Trigger background processing
        self._dispatch_background_pipeline(note.id, user_id, background_tasks)
        return note

    async def create_note(
        self,
        payload: NoteCreate,
        user_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> Note:
        tags: list[Tag] = []
        if payload.tag_names:
            for t_name in payload.tag_names:
                t = await self.tag_repo.get_or_create(t_name, user_id)
                tags.append(t)

        concepts: list[Concept] = []
        if payload.concept_names:
            for c_name in payload.concept_names:
                c = await self.concept_repo.get_or_create(c_name, user_id)
                concepts.append(c)

        note = await self.note_repo.create(
            user_id=user_id,
            title=payload.title,
            content=payload.content,
            source=payload.source,
            notebook_id=payload.notebook_id,
            processing_status=ProcessingStatus.PENDING,
            tags=tags,
            concepts=concepts,
        )
        await self.db.commit()

        self._dispatch_background_pipeline(note.id, user_id, background_tasks)
        return note

    async def update_note(
        self,
        note_id: str,
        payload: NoteUpdate,
        user_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> Note:
        note = await self.get_note(note_id, user_id)

        tags = None
        if payload.tag_names is not None:
            tags = []
            for t_name in payload.tag_names:
                t = await self.tag_repo.get_or_create(t_name, user_id)
                tags.append(t)

        concepts = None
        if payload.concept_names is not None:
            concepts = []
            for c_name in payload.concept_names:
                c = await self.concept_repo.get_or_create(c_name, user_id)
                concepts.append(c)

        content_changed = payload.content is not None and payload.content != note.content

        updated = await self.note_repo.update(
            note=note,
            title=payload.title,
            content=payload.content,
            summary=payload.summary,
            source=payload.source,
            notebook_id=payload.notebook_id,
            tags=tags,
            concepts=concepts,
            processing_status=ProcessingStatus.PENDING if content_changed else None,
        )
        await self.db.commit()

        if content_changed:
            self._dispatch_background_pipeline(updated.id, user_id, background_tasks)

        return updated

    async def delete(self, note_id: str, user_id: str) -> None:
        note = await self.get_note(note_id, user_id)
        await self.note_repo.delete(note)
        await self.db.commit()

    async def delete_note(self, note_id: str, user_id: str) -> None:
        await self.delete(note_id, user_id)

    def _dispatch_background_pipeline(
        self,
        note_id: str,
        user_id: str,
        background_tasks: BackgroundTasks | None = None,
    ):
        # Try Celery task first, fall back to FastAPI BackgroundTasks or asyncio Task
        dispatched = False
        try:
            from app.workers.tasks import process_note_task
            process_note_task.delay(note_id=note_id, user_id=user_id)
            dispatched = True
        except Exception:
            logger.info("Celery broker not connected, running as async background task")

        if not dispatched:
            if background_tasks:
                async def _task():
                    from app.db.session import AsyncSessionLocal
                    async with AsyncSessionLocal() as session:
                        await run_note_processing_pipeline(note_id, user_id, session)
                background_tasks.add_task(_task)
            else:
                async def _task_coro():
                    from app.db.session import AsyncSessionLocal
                    async with AsyncSessionLocal() as session:
                        await run_note_processing_pipeline(note_id, user_id, session)
                asyncio.create_task(_task_coro())
