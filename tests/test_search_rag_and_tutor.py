import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_rag_and_tutor(client: AsyncClient, auth_headers: dict):
    # 1. Create notes to search against
    await client.post(
        "/api/v1/notes",
        json={
            "title": "Retrieval-Augmented Generation",
            "content": "RAG connects an LLM to an external vector database for precise information retrieval.",
            "tag_names": ["AI", "RAG"],
            "concept_names": ["RAG", "Vector Search"],
        },
        headers=auth_headers,
    )

    # 2. Semantic search
    search_res = await client.get("/api/v1/search?q=retrieval", headers=auth_headers)
    assert search_res.status_code == 200
    results = search_res.json()["data"]
    assert len(results) >= 1
    assert "Retrieval" in results[0]["title"]

    # 3. Ask My Knowledge RAG
    ask_res = await client.post(
        "/api/v1/search/ask",
        json={"query": "What do I know about RAG?"},
        headers=auth_headers,
    )
    assert ask_res.status_code == 200
    ask_data = ask_res.json()["data"]
    assert "answer" in ask_data
    assert "sources" in ask_data
    assert len(ask_data["sources"]) >= 1

    # 4. AI Tutor Chat
    tutor_res = await client.post(
        "/api/v1/tutor/chat",
        json={
            "message": "Teach me RAG",
            "action": "teach",
            "history": [],
        },
        headers=auth_headers,
    )
    assert tutor_res.status_code == 200
    tutor_data = tutor_res.json()["data"]
    assert "response" in tutor_data
    assert "suggested_actions" in tutor_data

    # 5. AI Summarizer
    sum_res = await client.post(
        "/api/v1/ai/summarize",
        json={
            "content": "PostgreSQL with pgvector allows storing high-dimensional vector embeddings and performing cosine similarity searches efficiently alongside relational data.",
        },
        headers=auth_headers,
    )
    assert sum_res.status_code == 200
    sum_data = sum_res.json()["data"]
    assert "title" in sum_data
    assert "summary" in sum_data
    assert "key_concepts" in sum_data
