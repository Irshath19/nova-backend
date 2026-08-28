from abc import ABC, abstractmethod
from typing import Any

from app.schemas.ai import (
    DiscoveredRelationship,
    ExtractedConcept,
    SummarizeResponse,
)
from app.schemas.learning_path import GeneratedLearningPathResponse


class EmbeddingService(ABC):
    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """Generate a vector embedding for a single string of text."""

    @abstractmethod
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of strings."""


class AIProvider(ABC):
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the AI provider service is reachable."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> str:
        """Raw completion generation."""

    @abstractmethod
    async def summarize(self, content: str) -> SummarizeResponse:
        """Generate comprehensive structured summary of content."""

    @abstractmethod
    async def generate_tags(self, content: str) -> list[str]:
        """Generate normalized tags from content."""

    @abstractmethod
    async def extract_concepts(self, content: str) -> list[ExtractedConcept]:
        """Extract key domain concepts from content."""

    @abstractmethod
    async def discover_relationships(
        self,
        concepts_to_link: list[str],
        existing_concepts: list[str],
    ) -> list[DiscoveredRelationship]:
        """Discover semantic and structural relationships between new concepts and existing knowledge."""

    @abstractmethod
    async def generate_learning_path(
        self,
        topic: str,
        user_known_concepts: list[str],
    ) -> GeneratedLearningPathResponse:
        """Generate an ordered pedagogical learning path for a topic."""

    @abstractmethod
    async def tutor_chat(
        self,
        message: str,
        history: list[dict[str, str]],
        context_notes: list[dict[str, Any]],
        context_concepts: list[dict[str, Any]],
        action: str | None = None,
    ) -> str:
        """Generate personalized AI Tutor responses adapting to user's knowledge base."""
