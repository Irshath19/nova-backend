
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag


class TagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tag_id: str, user_id: str) -> Tag | None:
        stmt = select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, user_id: str) -> Tag | None:
        normalized = name.strip()
        stmt = select(Tag).where(
            Tag.user_id == user_id,
            func.lower(Tag.name) == normalized.lower(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str, user_id: str) -> Tag:
        normalized = name.strip()
        existing = await self.get_by_name(normalized, user_id)
        if existing:
            return existing

        tag = Tag(user_id=user_id, name=normalized)
        self.db.add(tag)
        await self.db.flush()
        return tag

    async def list_by_user(self, user_id: str) -> list[Tag]:
        stmt = select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
