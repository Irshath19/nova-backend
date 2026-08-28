import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.concept_repo import ConceptRepository
from app.repositories.note_repo import NoteRepository
from app.schemas.concept import ConceptOut
from app.schemas.search import (
    AskKnowledgeRequest,
    AskKnowledgeResponse,
    SearchResultItem,
    SourceReference,
)
from app.schemas.tag import TagOut
from app.services.ai.ollama import get_ai_provider, get_embedding_service


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.note_repo = NoteRepository(db)
        self.concept_repo = ConceptRepository(db)
        self.ai = get_ai_provider()
        self.embedding_svc = get_embedding_service()

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 20,
    ) -> list[SearchResultItem]:
        query_cleaned = query.strip()
        if not query_cleaned:
            return []

        query_emb = await self.embedding_svc.get_embedding(query_cleaned)
        scored_notes = await self.note_repo.semantic_search(
            user_id=user_id,
            query_embedding=query_emb,
            limit=limit,
            text_query=query_cleaned,
        )

        results: list[SearchResultItem] = []
        for note, score in scored_notes:
            content_snippet = note.summary or note.content[:200]
            if len(note.content) > 200 and not note.summary:
                content_snippet += "..."

            results.append(
                SearchResultItem(
                    id=note.id,
                    title=note.title,
                    excerpt=content_snippet,
                    source=note.source,
                    similarity=round(score, 3),
                    created_at=note.created_at,
                    tags=[TagOut.model_validate(t) for t in note.tags],
                    concepts=[ConceptOut.model_validate(c) for c in note.concepts],
                )
            )

        return results

    async def ask_my_knowledge(
        self,
        user_id: str,
        payload: AskKnowledgeRequest,
    ) -> AskKnowledgeResponse:
        query = payload.query.strip()
        query_emb = await self.embedding_svc.get_embedding(query)

        # Retrieve top 5 most relevant notes
        scored_notes = await self.note_repo.semantic_search(
            user_id=user_id,
            query_embedding=query_emb,
            limit=5,
            text_query=query,
        )

        # Retrieve top relevant concepts
        concept_tokens = [w for w in re.findall(r"\w+", query) if len(w) > 2]
        all_user_concepts = await self.concept_repo.list_by_user(user_id, limit=50)
        relevant_concepts = [
            c for c in all_user_concepts
            if any(t.lower() in c.name.lower() or (c.description and t.lower() in c.description.lower()) for t in concept_tokens)
        ][:5]

        # Filter notes with meaningful similarity
        relevant_notes = [note for note, score in scored_notes if score >= 0.05]
        sources: list[SourceReference] = []

        for note in relevant_notes:
            sources.append(
                SourceReference(
                    id=note.id,
                    title=note.title,
                    type="note",
                    excerpt=(note.summary or note.content[:150]),
                )
            )

        for concept in relevant_concepts:
            if not any(s.id == concept.id for s in sources):
                sources.append(
                    SourceReference(
                        id=concept.id,
                        title=concept.name,
                        type="concept",
                        excerpt=concept.description,
                    )
                )

        if not relevant_notes and not relevant_concepts:
            answer = (
                "You haven't recorded enough information about this topic for me to answer "
                "confidently from your knowledge base.\n\n"
                "Tip: You can use **Quick Capture** to record what you learn about this topic, "
                "and NOVA will automatically index it into your knowledge base."
            )
            return AskKnowledgeResponse(
                answer=answer,
                sources=[],
                confidence="insufficient_knowledge",
            )

        notes_data = [
            {"title": n.title, "content": n.content, "summary": n.summary}
            for n in relevant_notes
        ]
        concepts_data = [
            {"name": c.name, "description": c.description, "knowledge_level": c.knowledge_level.value}
            for c in relevant_concepts
        ]

        answer = await self.ai.tutor_chat(
            message=f"Answer this question based strictly on my knowledge: {query}",
            history=[],
            context_notes=notes_data,
            context_concepts=concepts_data,
            action="ask_my_knowledge",
        )

        return AskKnowledgeResponse(
            answer=answer,
            sources=sources,
            confidence="high" if len(relevant_notes) >= 2 else "medium",
        )
