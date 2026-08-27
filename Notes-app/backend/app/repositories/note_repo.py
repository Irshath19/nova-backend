import math
import re

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.concept import Concept
from app.models.note import Note, ProcessingStatus
from app.models.tag import Tag


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class NoteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, note_id: str, user_id: str) -> Note | None:
        stmt = (
            select(Note)
            .where(Note.id == note_id, Note.user_id == user_id)
            .options(
                selectinload(Note.tags),
                selectinload(Note.concepts),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: str,
        title: str,
        content: str,
        source: str | None = None,
        summary: str | None = None,
        processing_status: ProcessingStatus = ProcessingStatus.PENDING,
        tags: list[Tag] | None = None,
        concepts: list[Concept] | None = None,
    ) -> Note:
        note = Note(
            user_id=user_id,
            title=title,
            content=content,
            source=source,
            summary=summary,
            processing_status=processing_status,
        )
        if tags:
            note.tags = tags
        if concepts:
            note.concepts = concepts

        self.db.add(note)
        await self.db.flush()
        await self.db.refresh(note, ["tags", "concepts"])
        return note

    async def list_by_user(
        self,
        user_id: str,
        tag_id: str | None = None,
        concept_id: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Note], int]:
        stmt = select(Note).where(Note.user_id == user_id)
        count_stmt = select(func.count(Note.id)).where(Note.user_id == user_id)

        if tag_id:
            stmt = stmt.where(Note.tags.any(Tag.id == tag_id))
            count_stmt = count_stmt.where(Note.tags.any(Tag.id == tag_id))
        if concept_id:
            stmt = stmt.where(Note.concepts.any(Concept.id == concept_id))
            count_stmt = count_stmt.where(Note.concepts.any(Concept.id == concept_id))
        if search:
            search_filter = or_(
                Note.title.ilike(f"%{search}%"),
                Note.content.ilike(f"%{search}%"),
                Note.summary.ilike(f"%{search}%"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = (
            stmt.options(
                selectinload(Note.tags),
                selectinload(Note.concepts),
            )
            .order_by(Note.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update(
        self,
        note: Note,
        title: str | None = None,
        content: str | None = None,
        summary: str | None = None,
        source: str | None = None,
        processing_status: ProcessingStatus | None = None,
        embedding: list[float] | None = None,
        tags: list[Tag] | None = None,
        concepts: list[Concept] | None = None,
    ) -> Note:
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if summary is not None:
            note.summary = summary
        if source is not None:
            note.source = source
        if processing_status is not None:
            note.processing_status = processing_status
        if embedding is not None:
            note.embedding = embedding
        if tags is not None:
            note.tags = tags
        if concepts is not None:
            note.concepts = concepts

        await self.db.flush()
        return note

    async def delete(self, note: Note) -> None:
        await self.db.delete(note)
        await self.db.flush()

    async def semantic_search(
        self,
        user_id: str,
        query_embedding: list[float],
        limit: int = 10,
        text_query: str | None = None,
    ) -> list[tuple[Note, float]]:
        """
        Computes semantic similarity across user's notes with cosine similarity and text relevance.
        """
        stmt = (
            select(Note)
            .where(Note.user_id == user_id)
            .options(
                selectinload(Note.tags),
                selectinload(Note.concepts),
            )
        )
        result = await self.db.execute(stmt)
        notes = list(result.scalars().all())

        scored_notes: list[tuple[Note, float]] = []
        for n in notes:
            sim = 0.0
            if n.embedding:
                sim = _cosine_similarity(query_embedding, n.embedding)

            # Boost if keyword occurs in title or content
            if text_query:
                q_words = [w.lower() for w in re.findall(r"\w+", text_query) if len(w) > 2]
                title_lower = n.title.lower()
                content_lower = n.content.lower()
                for w in q_words:
                    if w in title_lower:
                        sim = max(sim, 0.4) + 0.3
                    elif w in content_lower:
                        sim = max(sim, 0.25) + 0.2

            sim = min(1.0, sim)
            if sim > 0.0:
                scored_notes.append((n, sim))

        scored_notes.sort(key=lambda x: x[1], reverse=True)
        return scored_notes[:limit]
