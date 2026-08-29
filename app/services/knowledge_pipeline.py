import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept, KnowledgeLevel
from app.models.note import Note, ProcessingStatus
from app.models.relationship import RelationshipType
from app.models.tag import Tag
from app.repositories.concept_repo import ConceptRepository
from app.repositories.note_repo import NoteRepository
from app.repositories.relationship_repo import RelationshipRepository
from app.repositories.tag_repo import TagRepository
from app.services.ai.ollama import get_ai_provider, get_embedding_service

logger = logging.getLogger(__name__)


async def run_note_processing_pipeline(note_id: str, user_id: str, db: AsyncSession) -> Note | None:
    """
    Executes the full asynchronous AI pipeline for a note:
    1. Summary Generation
    2. Smart Tags Extraction
    3. Concept Extraction & Deduplication
    4. Vector Embeddings Generation
    5. Knowledge Graph Relationship Discovery & Persistence
    6. Update Note Processing Status
    """
    note_repo = NoteRepository(db)
    tag_repo = TagRepository(db)
    concept_repo = ConceptRepository(db)
    rel_repo = RelationshipRepository(db)

    ai = get_ai_provider()
    embedding_svc = get_embedding_service()

    note = await note_repo.get_by_id(note_id, user_id)
    if not note:
        logger.error(f"Note {note_id} for user {user_id} not found")
        return None

    try:
        await note_repo.update(note, processing_status=ProcessingStatus.PROCESSING)
        await db.commit()

        # Sanitize HTML tags to clean plain text for AI processing
        import re
        clean_content = re.sub(r"<[^>]+>", " ", note.content)
        clean_content = re.sub(r"\s+", " ", clean_content).strip()
        if not clean_content:
            clean_content = note.title

        # Step 1: Clean Summary Generation (plain text without HTML tags)
        summary_res = await ai.summarize(clean_content)
        note_summary = summary_res.summary
        if note_summary:
            # Strip any residual HTML markup from summary
            note_summary = re.sub(r"<[^>]+>", "", note_summary).strip()

        # Step 2: Tags - Strictly preserve ONLY the user-provided tags (no AI tag generation)
        tag_entities: list[Tag] = list(note.tags)

        # Step 3: Concept Extraction & Deduplication
        extracted_concepts = await ai.extract_concepts(clean_content)
        concept_entities: list[Concept] = []
        new_concept_names: list[str] = []

        for c_data in extracted_concepts:
            concept_emb = await embedding_svc.get_embedding(f"{c_data.name}: {c_data.description}")
            concept = await concept_repo.get_or_create(
                name=c_data.name,
                user_id=user_id,
                description=c_data.description,
                knowledge_level=KnowledgeLevel.NEW,
                embedding=concept_emb,
            )
            if concept not in concept_entities:
                concept_entities.append(concept)
            new_concept_names.append(concept.name)

        for existing_c in note.concepts:
            if existing_c not in concept_entities:
                concept_entities.append(existing_c)

        # Step 4: Generate Note Vector Embedding
        note_embedding_text = f"{note.title}\n{note_summary}\n{clean_content}"
        note_vector = await embedding_svc.get_embedding(note_embedding_text)

        # Step 5: Knowledge Graph Relationship Discovery
        all_user_concepts = await concept_repo.list_by_user(user_id, limit=100)
        existing_concept_names = [
            c.name for c in all_user_concepts if c.name not in new_concept_names
        ]

        if new_concept_names and existing_concept_names:
            discovered_rels = await ai.discover_relationships(
                concepts_to_link=new_concept_names,
                existing_concepts=existing_concept_names[:30],
            )
            for r in discovered_rels:
                src_c = await concept_repo.get_by_name(r.source_concept, user_id)
                tgt_c = await concept_repo.get_by_name(r.target_concept, user_id)
                if src_c and tgt_c and src_c.id != tgt_c.id:
                    try:
                        rtype = RelationshipType(r.relationship_type)
                    except ValueError:
                        rtype = RelationshipType.RELATED_TO

                    await rel_repo.get_or_create(
                        user_id=user_id,
                        source_id=src_c.id,
                        target_id=tgt_c.id,
                        rel_type=rtype,
                        weight=0.9,
                    )

        # Step 6: Commit all updates
        await note_repo.update(
            note=note,
            summary=note_summary,
            processing_status=ProcessingStatus.COMPLETED,
            embedding=note_vector,
            tags=tag_entities,
            concepts=concept_entities,
        )
        await db.commit()
        await db.refresh(note, ["tags", "concepts"])
        logger.info(f"Note {note_id} successfully processed by AI pipeline with user-only tags.")
        return note


    except Exception as e:
        logger.exception(f"Error in note processing pipeline for {note_id}: {e}")
        await note_repo.update(note, processing_status=ProcessingStatus.FAILED)
        await db.commit()
        return note
