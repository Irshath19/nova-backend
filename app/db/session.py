from typing import AsyncGenerator

from pgvector.asyncpg import register_vector
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

Base = declarative_base()

# Create async engine with asyncpg vector registration
async def _init_connection(conn):
    await register_vector(conn)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG and False,
    future=True,
    pool_pre_ping=True,
    connect_args={"server_settings": {"search_path": "public"}},
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
