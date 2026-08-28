from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.concept import KnowledgeLevel


class ConceptBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = None
    knowledge_level: KnowledgeLevel = KnowledgeLevel.NEW


class ConceptCreate(ConceptBase):
    pass


class ConceptUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = None
    knowledge_level: KnowledgeLevel | None = None


class ConceptOut(ConceptBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class RelatedConceptSimple(BaseModel):
    id: str
    name: str
    relationship_type: str
    direction: str  # "outgoing" or "incoming"
    knowledge_level: KnowledgeLevel


class RelatedNoteSimple(BaseModel):
    id: str
    title: str
    summary: str | None = None
    created_at: datetime


class ConceptDetailOut(ConceptOut):
    related_concepts: list[RelatedConceptSimple] = []
    related_notes: list[RelatedNoteSimple] = []
    tags: list[str] = []
