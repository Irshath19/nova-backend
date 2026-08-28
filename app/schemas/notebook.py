from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotebookBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: str = Field("📚", max_length=20)
    description: str | None = None


class NotebookCreate(NotebookBase):
    pass


class NotebookUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    icon: str | None = Field(None, max_length=20)
    description: str | None = None


class NotebookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    icon: str = "📚"
    description: str | None = None
    created_at: datetime
    updated_at: datetime
