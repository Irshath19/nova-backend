import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, Base, engine
from app.models.concept import Concept, KnowledgeLevel
from app.models.learning_path import LearningPath, LearningPathItem, PathItemStatus
from app.models.note import Note, ProcessingStatus
from app.models.relationship import ConceptRelationship, RelationshipType
from app.models.tag import Tag
from app.models.user import User
from app.services.ai.ollama import get_embedding_service


async def seed_data():
    print("🌱 Starting NOVA development database seeding...")

    # 1. Create extension first and commit
    async with engine.connect() as conn:
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.commit()
    await engine.dispose()

    # 2. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    embedding_svc = get_embedding_service()

    async with AsyncSessionLocal() as session:
        # Check if demo user already exists
        from sqlalchemy import select
        existing_user = (await session.execute(select(User).where(User.email == "demo@nova.ai"))).scalar_one_or_none()

        if existing_user:
            print("ℹ️ Demo user already exists. Cleaning up existing demo data...")
            await session.delete(existing_user)
            await session.commit()

        # 1. Create Demo User
        demo_user = User(
            email="demo@nova.ai",
            username="nova_explorer",
            password_hash=hash_password("nova123456"),
        )
        session.add(demo_user)
        await session.flush()
        user_id = demo_user.id
        print("✅ Created Demo User: demo@nova.ai (password: nova123456)")

        # 2. Seed Tags
        tags_data = ["AI", "Architecture", "Databases", "Authentication", "LLM", "FullStack"]
        tag_entities = {}
        for t_name in tags_data:
            tag = Tag(user_id=user_id, name=t_name)
            session.add(tag)
            tag_entities[t_name] = tag
        await session.flush()
        print(f"✅ Created {len(tag_entities)} Tags")

        # 3. Seed Concepts with Knowledge Levels & Embeddings
        concepts_definitions = [
            (
                "LLM",
                "Large Language Models trained on massive text corpora using deep neural networks.",
                KnowledgeLevel.STRONG,
            ),
            (
                "Embeddings",
                "High-dimensional dense vector representations capturing semantic relationships between texts.",
                KnowledgeLevel.STRONG,
            ),
            (
                "Vector Search",
                "Retrieval technique using nearest-neighbor similarity (cosine / Euclidean) on vector embeddings.",
                KnowledgeLevel.INTERMEDIATE,
            ),
            (
                "RAG",
                "Retrieval-Augmented Generation: dynamic grounding of LLM responses using external retrieved context.",
                KnowledgeLevel.INTERMEDIATE,
            ),
            (
                "Agentic AI",
                "Autonomous AI systems equipped with tool use, persistent memory, and multi-step planning loops.",
                KnowledgeLevel.LEARNING,
            ),
            (
                "LangGraph",
                "Framework for building cyclic, stateful multi-agent workflows and resilient LLM applications.",
                KnowledgeLevel.LEARNING,
            ),
            (
                "PostgreSQL",
                "Advanced open-source relational database supporting relational data and vector indexing via pgvector.",
                KnowledgeLevel.STRONG,
            ),
            (
                "Redis",
                "In-memory key-value data store used for fast caching, pub/sub messaging, and task brokers.",
                KnowledgeLevel.STRONG,
            ),
            (
                "JWT",
                "JSON Web Tokens: compact, URL-safe means of representing claims securely between two parties.",
                KnowledgeLevel.STRONG,
            ),
            (
                "Chunking",
                "Splitting raw text documents into optimal semantic segments for embedding and retrieval.",
                KnowledgeLevel.FAMILIAR,
            ),
        ]

        concept_entities = {}
        for name, desc, level in concepts_definitions:
            emb = await embedding_svc.get_embedding(f"{name}: {desc}")
            concept = Concept(
                user_id=user_id,
                name=name,
                description=desc,
                knowledge_level=level,
                embedding=emb,
            )
            session.add(concept)
            concept_entities[name] = concept
        await session.flush()
        print(f"✅ Created {len(concept_entities)} Concepts")

        # 4. Seed Concept Relationships
        relationships_data = [
            ("RAG", "Embeddings", RelationshipType.USES, 1.0),
            ("RAG", "Vector Search", RelationshipType.USES, 1.0),
            ("RAG", "LLM", RelationshipType.DEPENDS_ON, 0.9),
            ("Vector Search", "Embeddings", RelationshipType.USES, 1.0),
            ("Agentic AI", "LLM", RelationshipType.USES, 1.0),
            ("Agentic AI", "LangGraph", RelationshipType.USES, 0.85),
            ("LangGraph", "Agentic AI", RelationshipType.PART_OF, 0.9),
            ("RAG", "Chunking", RelationshipType.USES, 0.8),
            ("Vector Search", "PostgreSQL", RelationshipType.RELATED_TO, 0.75),
            ("Agentic AI", "Redis", RelationshipType.USES, 0.65),
        ]

        for src, tgt, rel_type, weight in relationships_data:
            if src in concept_entities and tgt in concept_entities:
                rel = ConceptRelationship(
                    user_id=user_id,
                    source_concept_id=concept_entities[src].id,
                    target_concept_id=concept_entities[tgt].id,
                    relationship_type=rel_type,
                    weight=weight,
                )
                session.add(rel)
        await session.flush()
        print(f"✅ Created {len(relationships_data)} Concept Relationships")

        # 5. Seed Notes
        notes_data = [
            (
                "Understanding RAG Architecture",
                "Retrieval-Augmented Generation (RAG) is a technique that augments an LLM with external knowledge.\n\n"
                "Instead of relying purely on parameters learned during pretraining, RAG retrieves relevant document chunks from a vector database and includes them in the LLM context prompt.\n\n"
                "Key benefits:\n1. Reduces hallucinations\n2. Provides verifiable citations\n3. Updates domain knowledge without retraining.",
                "RAG combines retrieval with language generation to reduce hallucinations and ground LLM answers.",
                [tag_entities["AI"], tag_entities["LLM"]],
                [concept_entities["RAG"], concept_entities["Embeddings"], concept_entities["Vector Search"]],
            ),
            (
                "Vector Search Fundamentals",
                "Vector search converts unstructured documents into dense numerical vectors using embedding models like nomic-embed-text.\n\n"
                "When a query arrives, it is embedded into the same vector space, and similarity algorithms (such as Cosine Similarity or L2 distance) retrieve the nearest neighboring vectors efficiently using HNSW or IVFFlat indexes in pgvector.",
                "Vector search finds semantically similar content by computing cosine similarity between high-dimensional embeddings.",
                [tag_entities["Databases"], tag_entities["AI"]],
                [concept_entities["Vector Search"], concept_entities["Embeddings"], concept_entities["PostgreSQL"]],
            ),
            (
                "Building Autonomous Agents with LangGraph",
                "Agentic AI systems go beyond simple question-answering by maintaining stateful cyclic execution graphs.\n\n"
                "LangGraph allows modeling agentic control flows as graphs with nodes (actions / LLM calls) and conditional edges (decision routing). Agents can call tools, inspect responses, update scratchpad memory, and decide next actions iteratively.",
                "LangGraph enables cyclic, stateful agent architectures with tool calling and conditional routing.",
                [tag_entities["AI"], tag_entities["Architecture"]],
                [concept_entities["Agentic AI"], concept_entities["LangGraph"], concept_entities["LLM"]],
            ),
            (
                "JWT Authentication in Modern Web APIs",
                "JSON Web Tokens (JWT) allow stateless authentication between client and server.\n\n"
                "A standard pattern involves short-lived Access Tokens (e.g. 15-60 min) sent in the Authorization Bearer header, paired with longer-lived Refresh Tokens stored in secure HTTP-only cookies or encrypted local storage to safely rotate access tokens.",
                "JWT provides stateless bearer token authentication, often paired with refresh token rotation.",
                [tag_entities["Authentication"], tag_entities["FullStack"]],
                [concept_entities["JWT"]],
            ),
        ]

        for title, content, summary, note_tags, note_concepts in notes_data:
            note_emb = await embedding_svc.get_embedding(f"{title}\n{summary}\n{content}")
            note = Note(
                user_id=user_id,
                title=title,
                content=content,
                summary=summary,
                processing_status=ProcessingStatus.COMPLETED,
                embedding=note_emb,
                tags=note_tags,
                concepts=note_concepts,
            )
            session.add(note)
        await session.flush()
        print(f"✅ Created {len(notes_data)} Sample Notes")

        # 6. Seed Learning Path
        rag_path = LearningPath(
            user_id=user_id,
            title="Mastering Retrieval-Augmented Generation (RAG)",
            description="Comprehensive roadmap to mastering embeddings, vector databases, chunking, and full RAG pipeline architecture.",
        )
        session.add(rag_path)
        await session.flush()

        path_steps = [
            (concept_entities["LLM"], 0, PathItemStatus.COMPLETED),
            (concept_entities["Embeddings"], 1, PathItemStatus.COMPLETED),
            (concept_entities["Vector Search"], 2, PathItemStatus.IN_PROGRESS),
            (concept_entities["Chunking"], 3, PathItemStatus.NOT_STARTED),
            (concept_entities["RAG"], 4, PathItemStatus.NOT_STARTED),
        ]

        for concept, pos, status in path_steps:
            item = LearningPathItem(
                learning_path_id=rag_path.id,
                concept_id=concept.id,
                position=pos,
                status=status,
            )
            session.add(item)

        await session.commit()
        print("🎉 Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
