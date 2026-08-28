from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.concept_repo import ConceptRepository
from app.repositories.note_repo import NoteRepository
from app.schemas.search import SourceReference
from app.schemas.tutor import TutorChatRequest, TutorChatResponse
from app.services.ai.ollama import get_ai_provider, get_embedding_service


class TutorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.note_repo = NoteRepository(db)
        self.concept_repo = ConceptRepository(db)
        self.ai = get_ai_provider()
        self.embedding_svc = get_embedding_service()

    async def chat(self, user_id: str, payload: TutorChatRequest) -> TutorChatResponse:
        message = payload.message.strip()
        query_emb = await self.embedding_svc.get_embedding(message)

        # 1. Retrieve relevant notes
        scored_notes = await self.note_repo.semantic_search(
            user_id=user_id,
            query_embedding=query_emb,
            limit=4,
            text_query=message,
        )
        relevant_notes = [note for note, score in scored_notes if score >= 0.12]

        # 2. Retrieve relevant concepts
        relevant_concepts = await self.concept_repo.list_by_user(user_id, search=message, limit=5)
        if payload.concept_id:
            specific_concept = await self.concept_repo.get_by_id(payload.concept_id, user_id)
            if specific_concept and specific_concept not in relevant_concepts:
                relevant_concepts.insert(0, specific_concept)

        # 3. Format sources
        sources: list[SourceReference] = []
        for note in relevant_notes:
            sources.append(
                SourceReference(
                    id=note.id,
                    title=note.title,
                    type="note",
                    excerpt=note.summary or note.content[:150],
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

        # 4. Build prompt contexts
        notes_data = [
            {"title": n.title, "content": n.content, "summary": n.summary}
            for n in relevant_notes
        ]
        concepts_data = [
            {
                "name": c.name,
                "description": c.description,
                "knowledge_level": c.knowledge_level.value,
            }
            for c in relevant_concepts
        ]

        history_data = [{"role": m.role, "content": m.content} for m in payload.history]

        response_text = await self.ai.tutor_chat(
            message=message,
            history=history_data,
            context_notes=notes_data,
            context_concepts=concepts_data,
            action=payload.action,
        )

        suggested_actions = [
            "Explain this simply",
            "Give me a code example",
            "What am I missing?",
            "Create a learning path",
        ]

        return TutorChatResponse(
            response=response_text,
            suggested_actions=suggested_actions,
            sources=sources,
            related_concepts=[c.name for c in relevant_concepts[:5]],
        )
