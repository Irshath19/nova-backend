from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.concept import ConceptOut
from app.schemas.tag import TagOut


class SearchResultItem(BaseModel):
    id: str
    title: str
    excerpt: str
    source: str | None = None
    similarity: float
    created_at: datetime
    tags: list[TagOut] = []
    concepts: list[ConceptOut] = []


class SourceReference(BaseModel):
    id: str
    title: str
    type: str  # "note" or "concept"
    excerpt: str | None = None


class AskKnowledgeRequest(BaseModel):
    query: str = Field(..., min_length=2)


class AskKnowledgeResponse(BaseModel):
    answer: str
    sources: list[SourceReference] = []
    confidence: str  # "high", "medium", "insufficient_knowledge"
