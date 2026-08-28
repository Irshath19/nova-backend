from datetime import datetime

from pydantic import BaseModel


class ConceptLevelCount(BaseModel):
    level: str
    count: int


class GrowthDataPoint(BaseModel):
    date: str
    notes_count: int
    concepts_count: int


class PathProgressSummary(BaseModel):
    id: str
    title: str
    total_items: int
    completed_items: int
    progress_percentage: float


class RecentKnowledgeItem(BaseModel):
    id: str
    type: str  # "note" or "concept"
    title: str
    timestamp: datetime
    badge: str | None = None


class ProgressMetricsOut(BaseModel):
    total_notes: int
    total_concepts: int
    total_tags: int
    total_connections: int
    total_learning_paths: int
    completed_concepts: int
    learning_concepts: int
    concepts_by_level: list[ConceptLevelCount]
    learning_paths_progress: list[PathProgressSummary]
    growth_timeline: list[GrowthDataPoint]
    recent_knowledge: list[RecentKnowledgeItem]
