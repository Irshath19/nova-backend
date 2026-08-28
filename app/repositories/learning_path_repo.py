
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.learning_path import LearningPath, LearningPathItem, PathItemStatus


class LearningPathRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, path_id: str, user_id: str) -> LearningPath | None:
        stmt = (
            select(LearningPath)
            .where(LearningPath.id == path_id, LearningPath.user_id == user_id)
            .options(
                selectinload(LearningPath.items).selectinload(LearningPathItem.concept),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[LearningPath]:
        stmt = (
            select(LearningPath)
            .where(LearningPath.user_id == user_id)
            .options(
                selectinload(LearningPath.items).selectinload(LearningPathItem.concept),
            )
            .order_by(LearningPath.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        user_id: str,
        title: str,
        description: str | None = None,
        concept_ids: list[str] | None = None,
    ) -> LearningPath:
        path = LearningPath(
            user_id=user_id,
            title=title,
            description=description,
        )
        self.db.add(path)
        await self.db.flush()

        if concept_ids:
            for idx, cid in enumerate(concept_ids):
                item = LearningPathItem(
                    learning_path_id=path.id,
                    concept_id=cid,
                    position=idx,
                    status=PathItemStatus.NOT_STARTED,
                )
                self.db.add(item)
            await self.db.flush()

        await self.db.refresh(path)
        return path

    async def update(
        self,
        path: LearningPath,
        title: str | None = None,
        description: str | None = None,
    ) -> LearningPath:
        if title is not None:
            path.title = title
        if description is not None:
            path.description = description
        await self.db.flush()
        return path

    async def update_item(
        self,
        item_id: str,
        path_id: str,
        status: PathItemStatus | None = None,
        position: int | None = None,
    ) -> LearningPathItem | None:
        stmt = select(LearningPathItem).where(
            LearningPathItem.id == item_id,
            LearningPathItem.learning_path_id == path_id,
        )
        res = await self.db.execute(stmt)
        item = res.scalar_one_or_none()
        if item:
            if status is not None:
                item.status = status
            if position is not None:
                item.position = position
            await self.db.flush()
        return item

    async def delete(self, path: LearningPath) -> None:
        await self.db.delete(path)
        await self.db.flush()
