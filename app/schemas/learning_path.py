from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.learning_path import PathItemStatus
from app.schemas.concept import ConceptOut


class LearningPathStepInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    concept_id: str | None = None
    status: PathItemStatus | None = PathItemStatus.NOT_STARTED



class LearningPathItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    concept_id: str | None = None
    position: int = 0
    status: PathItemStatus = PathItemStatus.NOT_STARTED


class LearningPathItemUpdate(BaseModel):
    status: PathItemStatus | None = None
    position: int | None = None
    title: str | None = None
    description: str | None = None


class LearningPathItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    learning_path_id: str
    title: str
    description: str | None = None
    concept_id: str | None = None
    position: int
    status: PathItemStatus
    concept: ConceptOut | None = None


class LearningPathBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class LearningPathCreate(LearningPathBase):
    steps: list[LearningPathStepInput] | None = []
    concept_ids: list[str] | None = []


class LearningPathUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    steps: list[LearningPathStepInput] | None = None
    items: list[LearningPathItemCreate] | None = None



class LearningPathOut(LearningPathBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    total_items: int = 0
    completed_items: int = 0
    items: list[LearningPathItemOut] = []


class GeneratedPathStep(BaseModel):
    title: str
    description: str
    concept_name: str


class GeneratedLearningPathResponse(BaseModel):
    title: str
    description: str
    steps: list[GeneratedPathStep]
