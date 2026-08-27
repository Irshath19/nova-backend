import hashlib
import json
import logging
import math
import re
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.ai import (
    DiscoveredRelationship,
    ExtractedConcept,
    SummarizeResponse,
)
from app.schemas.learning_path import GeneratedLearningPathResponse, GeneratedPathStep
from app.services.ai.base import AIProvider, EmbeddingService
from app.services.ai.prompts.concept_extractor import (
    CONCEPT_EXTRACTOR_SYSTEM_PROMPT,
    CONCEPT_EXTRACTOR_USER_PROMPT,
)
from app.services.ai.prompts.learning_path import (
    LEARNING_PATH_SYSTEM_PROMPT,
    LEARNING_PATH_USER_PROMPT,
)
from app.services.ai.prompts.relationship_extractor import (
    RELATIONSHIP_EXTRACTOR_SYSTEM_PROMPT,
    RELATIONSHIP_EXTRACTOR_USER_PROMPT,
)
from app.services.ai.prompts.summarizer import (
    SUMMARIZER_SYSTEM_PROMPT,
    SUMMARIZER_USER_PROMPT,
)
from app.services.ai.prompts.tagger import (
    TAGGER_SYSTEM_PROMPT,
    TAGGER_USER_PROMPT,
)
from app.services.ai.prompts.tutor import (
    TUTOR_SYSTEM_PROMPT,
    TUTOR_USER_PROMPT,
)

logger = logging.getLogger(__name__)


def _extract_json_from_text(text: str) -> Any:
    """Safely extracts and parses JSON from raw LLM output, handling markdown blocks."""
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find first '{' or '[' and last '}' or ']'
        start_brace = cleaned.find("{")
        start_bracket = cleaned.find("[")
        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            end_brace = cleaned.rfind("}")
            if end_brace != -1:
                return json.loads(cleaned[start_brace : end_brace + 1])
        elif start_bracket != -1:
            end_bracket = cleaned.rfind("]")
            if end_bracket != -1:
                return json.loads(cleaned[start_bracket : end_bracket + 1])
        raise


def _deterministic_mock_embedding(text: str, dim: int = 768) -> list[float]:
    """Generates a deterministic unit-length vector for fallback/offline testing."""
    vec = []
    for i in range(dim):
        h = hashlib.sha256(f"{text}:{i}".encode()).hexdigest()
        val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
        vec.append(val)
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


class OllamaEmbeddingService(EmbeddingService):
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_EMBEDDING_MODEL
        self.dim = settings.EMBEDDING_DIMENSION

    async def get_embedding(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Ollama embeddings endpoint
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding")
                    if embedding and isinstance(embedding, list):
                        # Ensure correct dimension length
                        if len(embedding) == self.dim:
                            return embedding
                        elif len(embedding) < self.dim:
                            return embedding + [0.0] * (self.dim - len(embedding))
                        return embedding[: self.dim]
        except Exception as e:
            logger.warning(f"Ollama embedding request failed ({e}), using deterministic fallback.")

        return _deterministic_mock_embedding(text, self.dim)

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [await self.get_embedding(t) for t in texts]


class OllamaProvider(AIProvider):
    def __init__(
        self,
        base_url: str | None = None,
        chat_model: str | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.chat_model = chat_model or settings.OLLAMA_CHAT_MODEL
        self.embedding_service = embedding_service or OllamaEmbeddingService(self.base_url)

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.chat_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_schema or "JSON" in (system_prompt or ""):
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                if response.status_code == 200:
                    return response.json().get("response", "")
        except Exception as e:
            logger.warning(f"Ollama complete request failed: {e}")

        # Fallback response if Ollama is unreachable
        return ""

    async def summarize(self, content: str) -> SummarizeResponse:
        prompt = SUMMARIZER_USER_PROMPT.format(content=content)
        raw = await self.complete(
            prompt=prompt,
            system_prompt=SUMMARIZER_SYSTEM_PROMPT,
            json_schema={"type": "object"},
        )
        if raw:
            try:
                data = _extract_json_from_text(raw)
                return SummarizeResponse(
                    title=data.get("title", "Synthesized Knowledge"),
                    summary=data.get("summary", content[:200]),
                    key_concepts=data.get("key_concepts", []),
                    important_points=data.get("important_points", []),
                    practical_example=data.get("practical_example"),
                    related_concepts=data.get("related_concepts", []),
                    things_to_learn_next=data.get("things_to_learn_next", []),
                )
            except Exception as e:
                logger.warning(f"Failed to parse summarizer JSON: {e}")

        # Intelligent deterministic fallback
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        first_line = lines[0] if lines else "Note Summary"
        title = first_line[:60] if len(first_line) > 3 else "Knowledge Note"
        words = re.findall(r"\b[A-Z][a-zA-Z0-9_-]{2,}\b", content)
        unique_concepts = list(dict.fromkeys(words))[:5]
        return SummarizeResponse(
            title=title,
            summary=content[:250] + ("..." if len(content) > 250 else ""),
            key_concepts=unique_concepts or ["Core Concept"],
            important_points=[line[:100] for line in lines[:3]],
            practical_example="Review your captured notes to connect related ideas.",
            related_concepts=["Knowledge Management", "System Design"],
            things_to_learn_next=["Explore related concepts in the graph"],
        )

    async def generate_tags(self, content: str) -> list[str]:
        prompt = TAGGER_USER_PROMPT.format(content=content)
        raw = await self.complete(prompt=prompt, system_prompt=TAGGER_SYSTEM_PROMPT)
        if raw:
            try:
                data = _extract_json_from_text(raw)
                if isinstance(data, dict) and "tags" in data:
                    return [str(t).strip() for t in data["tags"] if str(t).strip()]
                elif isinstance(data, list):
                    return [str(t).strip() for t in data if str(t).strip()]
            except Exception as e:
                logger.warning(f"Failed to parse tags JSON: {e}")

        # Fallback tag extraction
        words = re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", content)
        tags = list(dict.fromkeys(words))[:4]
        return tags or ["Knowledge", "General"]

    async def extract_concepts(self, content: str) -> list[ExtractedConcept]:
        prompt = CONCEPT_EXTRACTOR_USER_PROMPT.format(content=content)
        raw = await self.complete(prompt=prompt, system_prompt=CONCEPT_EXTRACTOR_SYSTEM_PROMPT)
        if raw:
            try:
                data = _extract_json_from_text(raw)
                concepts_list = data.get("concepts", []) if isinstance(data, dict) else data
                extracted = []
                for item in concepts_list:
                    if isinstance(item, dict) and "name" in item:
                        extracted.append(
                            ExtractedConcept(
                                name=item["name"].strip(),
                                description=item.get("description", f"Concept representing {item['name']}"),
                                importance=float(item.get("importance", 1.0)),
                            )
                        )
                if extracted:
                    return extracted
            except Exception as e:
                logger.warning(f"Failed to parse concepts JSON: {e}")

        # Fallback concept extraction
        matches = list(dict.fromkeys(re.findall(r"\b[A-Z][a-zA-Z0-9\s-]{2,30}\b", content)))[:4]
        return [
            ExtractedConcept(
                name=m.strip(),
                description=f"Key concept extracted from note regarding {m.strip()}.",
                importance=0.8,
            )
            for m in matches
            if m.strip()
        ]

    async def discover_relationships(
        self,
        concepts_to_link: list[str],
        existing_concepts: list[str],
    ) -> list[DiscoveredRelationship]:
        if not concepts_to_link or not existing_concepts:
            return []

        prompt = RELATIONSHIP_EXTRACTOR_USER_PROMPT.format(
            new_concepts=json.dumps(concepts_to_link),
            existing_concepts=json.dumps(existing_concepts),
        )
        raw = await self.complete(
            prompt=prompt,
            system_prompt=RELATIONSHIP_EXTRACTOR_SYSTEM_PROMPT,
        )
        if raw:
            try:
                data = _extract_json_from_text(raw)
                rels_list = data.get("relationships", []) if isinstance(data, dict) else data
                results = []
                valid_types = {"RELATED_TO", "DEPENDS_ON", "PART_OF", "USES", "LEADS_TO"}
                for r in rels_list:
                    if isinstance(r, dict) and "source_concept" in r and "target_concept" in r:
                        rtype = r.get("relationship_type", "RELATED_TO").upper()
                        if rtype not in valid_types:
                            rtype = "RELATED_TO"
                        results.append(
                            DiscoveredRelationship(
                                source_concept=r["source_concept"].strip(),
                                target_concept=r["target_concept"].strip(),
                                relationship_type=rtype,
                                reason=r.get("reason", "Semantic association"),
                            )
                        )
                if results:
                    return results
            except Exception as e:
                logger.warning(f"Failed to parse relationships JSON: {e}")

        # Default relationship discovery logic
        results = []
        for n in concepts_to_link:
            for e in existing_concepts:
                if n.lower() != e.lower() and (n.lower() in e.lower() or e.lower() in n.lower()):
                    results.append(
                        DiscoveredRelationship(
                            source_concept=n,
                            target_concept=e,
                            relationship_type="RELATED_TO",
                            reason=f"{n} shares technical domain with {e}",
                        )
                    )
        return results

    async def generate_learning_path(
        self,
        topic: str,
        user_known_concepts: list[str],
    ) -> GeneratedLearningPathResponse:
        prompt = LEARNING_PATH_USER_PROMPT.format(
            topic=topic,
            user_known_concepts=json.dumps(user_known_concepts),
        )
        raw = await self.complete(prompt=prompt, system_prompt=LEARNING_PATH_SYSTEM_PROMPT)
        if raw:
            try:
                data = _extract_json_from_text(raw)
                steps = [
                    GeneratedPathStep(
                        title=s.get("title", s.get("concept_name", "Step")),
                        description=s.get("description", "Master this topic"),
                        concept_name=s.get("concept_name", s.get("title", "Concept")),
                    )
                    for s in data.get("steps", [])
                ]
                return GeneratedLearningPathResponse(
                    title=data.get("title", f"Mastering {topic}"),
                    description=data.get("description", f"Step-by-step roadmap to learn {topic}."),
                    steps=steps,
                )
            except Exception as e:
                logger.warning(f"Failed to parse learning path JSON: {e}")

        # Fallback learning path
        return GeneratedLearningPathResponse(
            title=f"Learning Path: {topic}",
            description=f"Structured curriculum to master {topic} from fundamentals to advanced patterns.",
            steps=[
                GeneratedPathStep(
                    title=f"{topic} Fundamentals",
                    description=f"Core concepts, mental model, and foundational vocabulary for {topic}.",
                    concept_name=f"{topic} Fundamentals",
                ),
                GeneratedPathStep(
                    title="Core Architecture & Components",
                    description="Deep dive into the underlying architecture and operational components.",
                    concept_name=f"{topic} Architecture",
                ),
                GeneratedPathStep(
                    title="Practical Implementation & Patterns",
                    description="Hands-on building, code examples, and best practice patterns.",
                    concept_name=f"{topic} Implementation",
                ),
                GeneratedPathStep(
                    title="Advanced Optimization & Scaling",
                    description="Performance tuning, evaluation metrics, and scaling strategies.",
                    concept_name=f"{topic} Optimization",
                ),
            ],
        )

    async def tutor_chat(
        self,
        message: str,
        history: list[dict[str, str]],
        context_notes: list[dict[str, Any]],
        context_concepts: list[dict[str, Any]],
        action: str | None = None,
    ) -> str:
        notes_str = (
            "\n".join(f"- Title: {n.get('title')}\n  Content: {n.get('content')}" for n in context_notes)
            if context_notes
            else "No specific matching notes found in your knowledge base."
        )
        concepts_str = (
            "\n".join(
                f"- Concept: {c.get('name')} (Level: {c.get('knowledge_level')})\n  Description: {c.get('description')}"
                for c in context_concepts
            )
            if context_concepts
            else "No matching concepts recorded yet."
        )
        history_str = "\n".join(f"{h.get('role', 'user').title()}: {h.get('content')}" for h in history[-6:])

        prompt = TUTOR_USER_PROMPT.format(
            notes_context=notes_str,
            concepts_context=concepts_str,
            conversation_history=history_str or "Start of conversation",
            user_message=message,
        )

        system = TUTOR_SYSTEM_PROMPT.format(action=action or "general_explanation")
        raw = await self.complete(prompt=prompt, system_prompt=system, temperature=0.3)
        if raw and raw.strip():
            return raw.strip()

        # Fallback tutor answer if LLM is offline
        if context_notes or context_concepts:
            sources_summary = ", ".join(n.get("title", "") for n in context_notes if n.get("title"))
            return (
                f"Based on your knowledge base (including {sources_summary or 'your recorded concepts'}):\n\n"
                f"You have captured notes related to this topic. To review the specifics, check your concept cards and linked notes in the Knowledge Graph."
            )
        else:
            return (
                "You haven't recorded enough information about this topic for me to answer confidently from your knowledge base.\n\n"
                f"Based on general technical knowledge:\n{message} is a foundational technical domain. You can capture notes about it using Quick Capture, and NOVA will index it into your personal knowledge graph."
            )


# Factory functions to get current AI provider based on settings
def get_ai_provider() -> AIProvider:
    provider = (settings.AI_PROVIDER or "").lower()
    if provider == "gemini":
        from app.services.ai.gemini import GeminiProvider
        return GeminiProvider()
    elif provider in ("openai", "chatgpt"):
        from app.services.ai.openai_provider import OpenAIProvider
        return OpenAIProvider()
    return OllamaProvider()


def get_embedding_service() -> EmbeddingService:
    provider = (settings.AI_PROVIDER or "").lower()
    if provider == "gemini":
        from app.services.ai.gemini import GeminiEmbeddingService
        return GeminiEmbeddingService()
    elif provider in ("openai", "chatgpt"):
        from app.services.ai.openai_provider import OpenAIEmbeddingService
        return OpenAIEmbeddingService()
    return OllamaEmbeddingService()
