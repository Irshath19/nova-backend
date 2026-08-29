import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_learning_paths_and_progress(client: AsyncClient, auth_headers: dict):
    # 1. Create a concept
    c_res = await client.post(
        "/api/v1/concepts",
        json={"name": "Neural Networks", "description": "Layered computation units"},
        headers=auth_headers,
    )
    concept_id = c_res.json()["data"]["id"]

    # 2. Create learning path with custom steps
    path_res = await client.post(
        "/api/v1/learning-paths",
        json={
            "title": "AI Engineering",
            "description": "Mastering autonomous AI systems",
            "steps": [
                {"title": "Python Core", "description": "Core python fundamentals"},
                {"title": "PyTorch", "description": "Deep learning models"},
            ],
        },
        headers=auth_headers,
    )
    assert path_res.status_code == 201
    path_data = path_res.json()["data"]
    path_id = path_data["id"]
    assert len(path_data["items"]) == 2
    assert path_data["items"][0]["title"] == "Python Core"
    assert path_data["items"][1]["title"] == "PyTorch"
    item_id = path_data["items"][0]["id"]


    # 3. Update path item status
    update_item_res = await client.put(
        f"/api/v1/learning-paths/{path_id}/items/{item_id}",
        json={"status": "COMPLETED"},
        headers=auth_headers,
    )
    assert update_item_res.status_code == 200
    assert update_item_res.json()["data"]["completed_items"] == 1

    # 4. Edit learning path
    edit_path_res = await client.put(
        f"/api/v1/learning-paths/{path_id}",
        json={
            "title": "AI & ML Engineering",
            "description": "Updated roadmap",
            "steps": [
                {"title": "Python Core", "description": "Core python fundamentals", "status": "COMPLETED"},
                {"title": "PyTorch", "description": "Deep learning models", "status": "NOT_STARTED"},
                {"title": "LLMs & Transformers", "description": "Attention mechanics", "status": "NOT_STARTED"},
            ],
        },
        headers=auth_headers,
    )
    assert edit_path_res.status_code == 200
    assert edit_path_res.json()["data"]["title"] == "AI & ML Engineering"
    assert len(edit_path_res.json()["data"]["items"]) == 3


    # 4. Generate learning path with AI
    gen_res = await client.post(
        "/api/v1/learning-paths/generate",
        json={"topic": "Agentic AI"},
        headers=auth_headers,
    )
    assert gen_res.status_code == 200
    gen_data = gen_res.json()["data"]
    assert "title" in gen_data
    assert len(gen_data["steps"]) >= 1

    # 5. Check Progress Metrics (Real Data Verification)
    progress_res = await client.get("/api/v1/progress", headers=auth_headers)
    assert progress_res.status_code == 200
    metrics = progress_res.json()["data"]
    assert metrics["total_concepts"] >= 1
    assert metrics["total_learning_paths"] >= 1
    assert len(metrics["concepts_by_level"]) == 5
    assert len(metrics["learning_paths_progress"]) >= 1
    assert metrics["learning_paths_progress"][0]["progress_percentage"] == round(1 / 3 * 100, 1)


