
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept, KnowledgeLevel
from app.repositories.concept_repo import ConceptRepository
from app.repositories.relationship_repo import RelationshipRepository
from app.schemas.concept import (
    ConceptCreate,
    ConceptDetailOut,
    ConceptUpdate,
    RelatedConceptSimple,
    RelatedNoteSimple,
)


class ConceptService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.concept_repo = ConceptRepository(db)
        self.rel_repo = RelationshipRepository(db)

    async def get_concept(self, concept_id: str, user_id: str) -> Concept:
        concept = await self.concept_repo.get_by_id(concept_id, user_id)
        if not concept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
        return concept

    async def get_concept_detail(self, concept_id: str, user_id: str) -> ConceptDetailOut:
        concept = await self.get_concept(concept_id, user_id)

        # Related concepts from relationships
        related_concepts_list: list[RelatedConceptSimple] = []
        relationships = await self.rel_repo.list_for_concept(concept_id, user_id)

        for rel in relationships:
            if rel.source_concept_id == concept_id and rel.target_concept:
                related_concepts_list.append(
                    RelatedConceptSimple(
                        id=rel.target_concept.id,
                        name=rel.target_concept.name,
                        relationship_type=rel.relationship_type.value,
                        direction="outgoing",
                        knowledge_level=rel.target_concept.knowledge_level,
                    )
                )
            elif rel.target_concept_id == concept_id and rel.source_concept:
                related_concepts_list.append(
                    RelatedConceptSimple(
                        id=rel.source_concept.id,
                        name=rel.source_concept.name,
                        relationship_type=rel.relationship_type.value,
                        direction="incoming",
                        knowledge_level=rel.source_concept.knowledge_level,
                    )
                )

        # Related notes
        related_notes_list = [
            RelatedNoteSimple(
                id=n.id,
                title=n.title,
                summary=n.summary,
                created_at=n.created_at,
            )
            for n in concept.notes
        ]

        # Gather tags from related notes
        tags_set = set()
        for n in concept.notes:
            for t in n.tags:
                tags_set.add(t.name)

        return ConceptDetailOut(
            id=concept.id,
            user_id=concept.user_id,
            name=concept.name,
            description=concept.description,
            knowledge_level=concept.knowledge_level,
            created_at=concept.created_at,
            updated_at=concept.updated_at,
            related_concepts=related_concepts_list,
            related_notes=related_notes_list,
            tags=sorted(list(tags_set)),
        )

    async def list_concepts(
        self,
        user_id: str,
        knowledge_level: KnowledgeLevel | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Concept]:
        return await self.concept_repo.list_by_user(
            user_id=user_id,
            knowledge_level=knowledge_level,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def create_concept(self, payload: ConceptCreate, user_id: str) -> Concept:
        concept = await self.concept_repo.get_or_create(
            name=payload.name,
            user_id=user_id,
            description=payload.description,
            knowledge_level=payload.knowledge_level,
        )
        await self.db.commit()
        return concept

    async def update_concept(
        self, concept_id: str, payload: ConceptUpdate, user_id: str
    ) -> Concept:
        concept = await self.get_concept(concept_id, user_id)
        updated = await self.concept_repo.update(
            concept=concept,
            name=payload.name,
            description=payload.description,
            knowledge_level=payload.knowledge_level,
        )
        await self.db.commit()
        return updated

    async def delete_concept(self, concept_id: str, user_id: str) -> None:
        concept = await self.get_concept(concept_id, user_id)
        await self.concept_repo.delete(concept)
        await self.db.commit()
