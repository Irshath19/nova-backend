
from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    content: str = Field(..., min_length=10)
    note_id: str | None = None


class SummarizeResponse(BaseModel):
    title: str
    summary: str
    key_concepts: list[str] = []
    important_points: list[str] = []
    practical_example: str | None = None
    related_concepts: list[str] = []
    things_to_learn_next: list[str] = []


class ExtractedConcept(BaseModel):
    name: str
    description: str
    importance: float = 1.0


class ExtractConceptsRequest(BaseModel):
    content: str = Field(..., min_length=10)


class ExtractConceptsResponse(BaseModel):
    concepts: list[ExtractedConcept] = []


class GenerateTagsRequest(BaseModel):
    content: str = Field(..., min_length=10)


class GenerateTagsResponse(BaseModel):
    tags: list[str] = []


class DiscoveredRelationship(BaseModel):
    source_concept: str
    target_concept: str
    relationship_type: str  # RELATED_TO, DEPENDS_ON, PART_OF, USES, LEADS_TO
    reason: str


class DiscoverRelationshipsResponse(BaseModel):
    relationships: list[DiscoveredRelationship] = []


class NoteProcessingResult(BaseModel):
    summary: str
    tags: list[str] = []
    concepts: list[ExtractedConcept] = []
    relationships: list[DiscoveredRelationship] = []
