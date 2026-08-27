
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.concept import Concept, KnowledgeLevel


class ConceptRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, concept_id: str, user_id: str) -> Concept | None:
        stmt = (
            select(Concept)
            .where(Concept.id == concept_id, Concept.user_id == user_id)
            .options(
                selectinload(Concept.notes),
                selectinload(Concept.outgoing_relationships),
                selectinload(Concept.incoming_relationships),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, user_id: str) -> Concept | None:
        normalized = name.strip()
        stmt = select(Concept).where(
            Concept.user_id == user_id,
            func.lower(Concept.name) == normalized.lower(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        name: str,
        user_id: str,
        description: str | None = None,
        knowledge_level: KnowledgeLevel = KnowledgeLevel.NEW,
        embedding: list[float] | None = None,
    ) -> Concept:
        normalized = name.strip()
        existing = await self.get_by_name(normalized, user_id)
        if existing:
            if description and (not existing.description or len(description) > len(existing.description)):
                existing.description = description
            if embedding and not existing.embedding:
                existing.embedding = embedding
            return existing

        concept = Concept(
            user_id=user_id,
            name=normalized,
            description=description,
            knowledge_level=knowledge_level,
            embedding=embedding,
        )
        self.db.add(concept)
        await self.db.flush()
        return concept

    async def list_by_user(
        self,
        user_id: str,
        knowledge_level: KnowledgeLevel | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Concept]:
        stmt = select(Concept).where(Concept.user_id == user_id)
        if knowledge_level:
            stmt = stmt.where(Concept.knowledge_level == knowledge_level)
        if search:
            stmt = stmt.where(
                Concept.name.ilike(f"%{search}%") | Concept.description.ilike(f"%{search}%")
            )
        stmt = (
            stmt.options(
                selectinload(Concept.notes),
            )
            .order_by(Concept.name)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        stmt = select(func.count(Concept.id)).where(Concept.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def update(
        self,
        concept: Concept,
        name: str | None = None,
        description: str | None = None,
        knowledge_level: KnowledgeLevel | None = None,
    ) -> Concept:
        if name:
            concept.name = name.strip()
        if description is not None:
            concept.description = description
        if knowledge_level:
            concept.knowledge_level = knowledge_level
        await self.db.flush()
        return concept

    async def delete(self, concept: Concept) -> None:
        await self.db.delete(concept)
        await self.db.flush()
