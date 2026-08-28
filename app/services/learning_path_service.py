from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_path import PathItemStatus
from app.repositories.concept_repo import ConceptRepository
from app.repositories.learning_path_repo import LearningPathRepository
from app.schemas.learning_path import (
    GeneratedLearningPathResponse,
    LearningPathCreate,
    LearningPathItemOut,
    LearningPathItemUpdate,
    LearningPathOut,
)
from app.services.ai.ollama import get_ai_provider


class LearningPathService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.path_repo = LearningPathRepository(db)
        self.concept_repo = ConceptRepository(db)
        self.ai = get_ai_provider()

    async def get_path(self, path_id: str, user_id: str) -> LearningPathOut:
        path = await self.path_repo.get_by_id(path_id, user_id)
        if not path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")

        total = len(path.items)
        completed = sum(1 for i in path.items if i.status == PathItemStatus.COMPLETED)

        return LearningPathOut(
            id=path.id,
            user_id=path.user_id,
            title=path.title,
            description=path.description,
            created_at=path.created_at,
            updated_at=path.updated_at,
            total_items=total,
            completed_items=completed,
            items=[LearningPathItemOut.model_validate(item) for item in path.items],
        )

    async def list_paths(self, user_id: str) -> list[LearningPathOut]:
        paths = await self.path_repo.list_by_user(user_id)
        result = []
        for path in paths:
            total = len(path.items)
            completed = sum(1 for i in path.items if i.status == PathItemStatus.COMPLETED)
            result.append(
                LearningPathOut(
                    id=path.id,
                    user_id=path.user_id,
                    title=path.title,
                    description=path.description,
                    created_at=path.created_at,
                    updated_at=path.updated_at,
                    total_items=total,
                    completed_items=completed,
                    items=[LearningPathItemOut.model_validate(item) for item in path.items],
                )
            )
        return result

    async def create_path(self, user_id: str, payload: LearningPathCreate) -> LearningPathOut:
        path = await self.path_repo.create(
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            concept_ids=payload.concept_ids,
        )
        await self.db.commit()
        return await self.get_path(path.id, user_id)

    async def update_item_status(
        self,
        path_id: str,
        item_id: str,
        user_id: str,
        payload: LearningPathItemUpdate,
    ) -> LearningPathOut:
        # Verify path belongs to user
        await self.get_path(path_id, user_id)

        item = await self.path_repo.update_item(
            item_id=item_id,
            path_id=path_id,
            status=payload.status,
            position=payload.position,
        )
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path item not found")

        await self.db.commit()
        return await self.get_path(path_id, user_id)

    async def delete_path(self, path_id: str, user_id: str) -> None:
        path = await self.path_repo.get_by_id(path_id, user_id)
        if not path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
        await self.path_repo.delete(path)
        await self.db.commit()

    async def generate_with_ai(
        self,
        user_id: str,
        topic: str,
    ) -> GeneratedLearningPathResponse:
        user_concepts = await self.concept_repo.list_by_user(user_id, limit=50)
        concept_names = [c.name for c in user_concepts]

        generated = await self.ai.generate_learning_path(
            topic=topic,
            user_known_concepts=concept_names,
        )
        return generated
