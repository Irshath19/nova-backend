import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_concepts_crud_and_graph(client: AsyncClient, auth_headers: dict):
    # 1. Create concepts
    c1_res = await client.post(
        "/api/v1/concepts",
        json={
            "name": "Embeddings",
            "description": "Dense vector representations of text",
            "knowledge_level": "STRONG",
        },
        headers=auth_headers,
    )
    assert c1_res.status_code == 201
    c1 = c1_res.json()["data"]
    assert c1["knowledge_level"] == "STRONG"

    c2_res = await client.post(
        "/api/v1/concepts",
        json={
            "name": "Vector Search",
            "description": "Nearest neighbor retrieval in high dimensional space",
            "knowledge_level": "INTERMEDIATE",
        },
        headers=auth_headers,
    )
    assert c2_res.status_code == 201
    c2 = c2_res.json()["data"]

    # 2. Duplicate concept creation should return existing
    dup_res = await client.post(
        "/api/v1/concepts",
        json={"name": "embeddings", "description": "Duplicate embedding"},
        headers=auth_headers,
    )
    assert dup_res.status_code == 201
    assert dup_res.json()["data"]["id"] == c1["id"]

    # 3. Update concept level
    up_res = await client.put(
        f"/api/v1/concepts/{c2['id']}",
        json={"knowledge_level": "STRONG"},
        headers=auth_headers,
    )
    assert up_res.status_code == 200
    assert up_res.json()["data"]["knowledge_level"] == "STRONG"

    # 4. Get concept detail
    detail_res = await client.get(f"/api/v1/concepts/{c1['id']}", headers=auth_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert detail["name"] == "Embeddings"

    # 5. Get graph
    graph_res = await client.get("/api/v1/graph", headers=auth_headers)
    assert graph_res.status_code == 200
    graph_data = graph_res.json()["data"]
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert len(graph_data["nodes"]) >= 2
