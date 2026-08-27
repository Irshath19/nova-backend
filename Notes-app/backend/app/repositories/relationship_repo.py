
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.relationship import ConceptRelationship, RelationshipType


class RelationshipRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_existing(
        self,
        user_id: str,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType,
    ) -> ConceptRelationship | None:
        stmt = select(ConceptRelationship).where(
            ConceptRelationship.user_id == user_id,
            ConceptRelationship.source_concept_id == source_id,
            ConceptRelationship.target_concept_id == target_id,
            ConceptRelationship.relationship_type == rel_type,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        user_id: str,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType = RelationshipType.RELATED_TO,
        weight: float = 1.0,
    ) -> ConceptRelationship:
        if source_id == target_id:
            raise ValueError("Source and target concepts cannot be identical")

        existing = await self.get_existing(user_id, source_id, target_id, rel_type)
        if existing:
            return existing

        rel = ConceptRelationship(
            user_id=user_id,
            source_concept_id=source_id,
            target_concept_id=target_id,
            relationship_type=rel_type,
            weight=weight,
        )
        self.db.add(rel)
        await self.db.flush()
        return rel

    async def list_by_user(self, user_id: str) -> list[ConceptRelationship]:
        stmt = (
            select(ConceptRelationship)
            .where(ConceptRelationship.user_id == user_id)
            .options(
                selectinload(ConceptRelationship.source_concept),
                selectinload(ConceptRelationship.target_concept),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_for_concept(self, concept_id: str, user_id: str) -> list[ConceptRelationship]:
        stmt = (
            select(ConceptRelationship)
            .where(
                ConceptRelationship.user_id == user_id,
                (ConceptRelationship.source_concept_id == concept_id)
                | (ConceptRelationship.target_concept_id == concept_id),
            )
            .options(
                selectinload(ConceptRelationship.source_concept),
                selectinload(ConceptRelationship.target_concept),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
