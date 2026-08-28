import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "email": "alice@nova.ai",
        "username": "alice",
        "password": "securepassword123",
    }
    res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    data = res.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "alice@nova.ai"
    assert data["user"]["username"] == "alice"

    # 2. Duplicate registration should fail
    dup_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 400

    # 3. Login with email
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "alice@nova.ai", "password": "securepassword123"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()["data"]
    assert "access_token" in login_data

    # 4. Login with username
    login_username_res = await client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "alice", "password": "securepassword123"},
    )
    assert login_username_res.status_code == 200

    # 5. Invalid credentials should fail
    bad_login_res = await client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "alice", "password": "wrongpassword"},
    )
    assert bad_login_res.status_code == 401


@pytest.mark.asyncio
async def test_get_me_and_refresh_token(client: AsyncClient, auth_headers: dict):
    # Get current user profile
    me_res = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == "testuser@nova.ai"

    # Test without auth token
    unauth_res = await client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401
