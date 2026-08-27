import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app

# In-memory SQLite async engine for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def init_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Helper fixture to register a test user and obtain auth headers."""
    register_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@nova.ai",
            "username": "testuser",
            "password": "password123",
        },
    )
    data = register_res.json()["data"]
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def second_user_auth_headers(client: AsyncClient) -> dict:
    """Helper fixture for testing user isolation."""
    register_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "otheruser@nova.ai",
            "username": "otheruser",
            "password": "password123",
        },
    )
    data = register_res.json()["data"]
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}
