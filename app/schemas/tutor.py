
from pydantic import BaseModel, Field

from app.schemas.search import SourceReference


class TutorMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class TutorChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    concept_id: str | None = None
    action: str | None = None  # "teach", "explain_simply", "give_example", "compare", "missing", "summarize", "create_path"
    history: list[TutorMessage] = []


class TutorChatResponse(BaseModel):
    response: str
    suggested_actions: list[str] = []
    sources: list[SourceReference] = []
    related_concepts: list[str] = []
