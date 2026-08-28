from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.note import ProcessingStatus
from app.schemas.concept import ConceptOut
from app.schemas.notebook import NotebookOut
from app.schemas.tag import TagOut


class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    source: str | None = None
    notebook_id: str | None = None


class NoteCreate(NoteBase):
    tag_names: list[str] | None = []
    concept_names: list[str] | None = []


class QuickCaptureRequest(BaseModel):
    content: str = Field(..., min_length=1)
    title: str | None = None
    source: str | None = None
    notebook_id: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = Field(None, min_length=1)
    summary: str | None = None
    source: str | None = None
    notebook_id: str | None = None
    tag_names: list[str] | None = None
    concept_names: list[str] | None = None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    content: str
    summary: str | None = None
    source: str | None = None
    notebook_id: str | None = None
    notebook: NotebookOut | None = None
    processing_status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
    tags: list[TagOut] = []
    concepts: list[ConceptOut] = []


class NoteListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    content: str
    summary: str | None = None
    source: str | None = None
    notebook_id: str | None = None
    notebook: NotebookOut | None = None
    processing_status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
    tags: list[TagOut] = []
    concepts: list[ConceptOut] = []
