from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept
from app.repositories.concept_repo import ConceptRepository
from app.repositories.relationship_repo import RelationshipRepository
from app.schemas.relationship import GraphEdge, GraphNode, GraphResponse


class GraphService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.concept_repo = ConceptRepository(db)
        self.rel_repo = RelationshipRepository(db)

    async def get_graph(
        self,
        user_id: str,
        concept_id: str | None = None,
        limit: int = 150,
    ) -> GraphResponse:
        all_concepts = await self.concept_repo.list_by_user(user_id, limit=limit)
        all_relationships = await self.rel_repo.list_by_user(user_id)

        concept_map: dict[str, Concept] = {c.id: c for c in all_concepts}
        connections_count: dict[str, int] = {c.id: 0 for c in all_concepts}

        # Filter by concept if concept-centered graph is requested
        if concept_id:
            relevant_concept_ids: set[str] = {concept_id}
            for rel in all_relationships:
                if rel.source_concept_id == concept_id:
                    relevant_concept_ids.add(rel.target_concept_id)
                elif rel.target_concept_id == concept_id:
                    relevant_concept_ids.add(rel.source_concept_id)

            all_relationships = [
                rel
                for rel in all_relationships
                if rel.source_concept_id in relevant_concept_ids
                and rel.target_concept_id in relevant_concept_ids
            ]
            all_concepts = [c for c in all_concepts if c.id in relevant_concept_ids]

        for rel in all_relationships:
            if rel.source_concept_id in connections_count:
                connections_count[rel.source_concept_id] += 1
            if rel.target_concept_id in connections_count:
                connections_count[rel.target_concept_id] += 1

        nodes = [
            GraphNode(
                id=c.id,
                name=c.name,
                knowledge_level=c.knowledge_level.value,
                notes_count=len(c.notes) if hasattr(c, "notes") and c.notes else 0,
                connections_count=connections_count.get(c.id, 0),
            )
            for c in all_concepts
        ]

        edges = [
            GraphEdge(
                id=rel.id,
                source=rel.source_concept_id,
                target=rel.target_concept_id,
                relationship_type=rel.relationship_type.value,
                weight=rel.weight,
            )
            for rel in all_relationships
            if rel.source_concept_id in concept_map and rel.target_concept_id in concept_map
        ]

        return GraphResponse(nodes=nodes, edges=edges)
