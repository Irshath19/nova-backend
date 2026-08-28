from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook import Notebook


class NotebookRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, notebook_id: str, user_id: str) -> Notebook | None:
        stmt = select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, user_id: str) -> Notebook | None:
        stmt = select(Notebook).where(Notebook.name == name, Notebook.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str, user_id: str, icon: str = "📚") -> Notebook:
        clean_name = name.strip()
        existing = await self.get_by_name(clean_name, user_id)
        if existing:
            return existing

        notebook = Notebook(
            user_id=user_id,
            name=clean_name,
            icon=icon,
        )
        self.db.add(notebook)
        await self.db.flush()
        await self.db.refresh(notebook)
        return notebook

    async def create(
        self,
        user_id: str,
        name: str,
        icon: str = "📚",
        description: str | None = None,
    ) -> Notebook:
        notebook = Notebook(
            user_id=user_id,
            name=name.strip(),
            icon=icon.strip() if icon else "📚",
            description=description,
        )
        self.db.add(notebook)
        await self.db.flush()
        await self.db.refresh(notebook)
        return notebook

    async def list_by_user(self, user_id: str) -> list[Notebook]:
        stmt = select(Notebook).where(Notebook.user_id == user_id).order_by(Notebook.name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, notebook: Notebook) -> None:
        await self.db.delete(notebook)
        await self.db.flush()
