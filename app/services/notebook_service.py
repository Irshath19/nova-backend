from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook import Notebook
from app.repositories.notebook_repo import NotebookRepository
from app.schemas.notebook import NotebookCreate


class NotebookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotebookRepository(db)

    async def list_notebooks(self, user_id: str) -> list[Notebook]:
        return await self.repo.list_by_user(user_id=user_id)

    async def create_notebook(self, payload: NotebookCreate, user_id: str) -> Notebook:
        existing = await self.repo.get_by_name(payload.name.strip(), user_id)
        if existing:
            return existing

        notebook = await self.repo.create(
            user_id=user_id,
            name=payload.name,
            icon=payload.icon,
            description=payload.description,
        )
        await self.db.commit()
        return notebook

    async def delete_notebook(self, notebook_id: str, user_id: str) -> None:
        notebook = await self.repo.get_by_id(notebook_id, user_id)
        if not notebook:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
        await self.repo.delete(notebook)
        await self.db.commit()
