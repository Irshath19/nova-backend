from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.relationship import RelationshipType


class RelationshipCreate(BaseModel):
    source_concept_id: str
    target_concept_id: str
    relationship_type: RelationshipType = RelationshipType.RELATED_TO
    weight: float = Field(1.0, ge=0.0, le=1.0)


class RelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    source_concept_id: str
    target_concept_id: str
    relationship_type: RelationshipType
    weight: float
    created_at: datetime


class GraphNode(BaseModel):
    id: str
    name: str
    knowledge_level: str
    notes_count: int = 0
    connections_count: int = 0


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: str
    weight: float = 1.0


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
