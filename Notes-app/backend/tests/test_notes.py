import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_quick_capture_and_notes_crud(
    client: AsyncClient,
    auth_headers: dict,
    second_user_auth_headers: dict,
):
    # 1. Quick capture a note
    qc_res = await client.post(
        "/api/v1/notes/quick-capture",
        json={"content": "JWT is a stateless authentication mechanism that uses digital signatures."},
        headers=auth_headers,
    )
    assert qc_res.status_code == 201
    note = qc_res.json()["data"]
    note_id = note["id"]
    assert note["content"].startswith("JWT is a stateless")
    assert note["title"] != ""

    # 2. Get note by ID
    get_res = await client.get(f"/api/v1/notes/{note_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == note_id

    # 3. User isolation test: second user cannot access this note
    other_user_res = await client.get(f"/api/v1/notes/{note_id}", headers=second_user_auth_headers)
    assert other_user_res.status_code == 404

    # 4. Create structured note with tags and concepts
    create_res = await client.post(
        "/api/v1/notes",
        json={
            "title": "Understanding RAG",
            "content": "Retrieval-Augmented Generation connects vector search with LLMs.",
            "source": "https://nova.ai/docs",
            "tag_names": ["AI", "RAG"],
            "concept_names": ["RAG", "Vector Search"],
        },
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    created_note = create_res.json()["data"]
    assert len(created_note["tags"]) == 2
    assert len(created_note["concepts"]) == 2

    # 5. List notes with pagination
    list_res = await client.get("/api/v1/notes?page=1&limit=10", headers=auth_headers)
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert len(items) == 2

    # 6. Update note
    update_res = await client.put(
        f"/api/v1/notes/{note_id}",
        json={"title": "Updated JWT Note Title"},
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["title"] == "Updated JWT Note Title"

    # 7. Delete note
    del_res = await client.delete(f"/api/v1/notes/{note_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # 8. Note should no longer exist
    after_del = await client.get(f"/api/v1/notes/{note_id}", headers=auth_headers)
    assert after_del.status_code == 404
