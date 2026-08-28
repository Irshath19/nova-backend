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
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_brace = cleaned.find("{")
        start_bracket = cleaned.find("[")
        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            end_brace = cleaned.rfind("}")
            if end_brace != -1:
                try:
                    return json.loads(cleaned[start_brace : end_brace + 1])
                except json.JSONDecodeError:
                    pass
        elif start_bracket != -1:
            end_bracket = cleaned.rfind("]")
            if end_bracket != -1:
                try:
                    return json.loads(cleaned[start_bracket : end_bracket + 1])
                except json.JSONDecodeError:
                    pass
    return None


class OpenAIEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_EMBEDDING_MODEL
        self.dim = settings.EMBEDDING_DIMENSION
        self.base_url = "https://api.openai.com/v1"

    def _deterministic_fallback(self, text: str) -> list[float]:
        tokens = re.findall(r"\w+", text.lower())
        vec = [0.0] * self.dim
        if not tokens:
            vec[0] = 1.0
            return vec
        for i, token in enumerate(tokens):
            h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
            idx = h % self.dim
            val = ((h >> 8) % 1000) / 1000.0 - 0.5
            weight = 1.0 / math.sqrt(i + 1)
            vec[idx] += val * weight
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 6) for x in vec]

    async def get_embedding(self, text: str) -> list[float]:
        if not self.api_key:
            return self._deterministic_fallback(text)
        try:
            url = f"{self.base_url}/embeddings"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "input": text[:8000],
                "model": self.model,
                "dimensions": self.dim,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    values = data.get("data", [{}])[0].get("embedding", [])
                    if values:
                        return values[: self.dim]
                logger.warning(f"OpenAI embedding returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"OpenAI embedding failed: {e}. Using deterministic fallback.")
        return self._deterministic_fallback(text)

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [await self.get_embedding(t) for t in texts]


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.base_url = "https://api.openai.com/v1"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> str:
        if not self.api_key:
            return ""
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if json_schema:
                payload["response_format"] = {"type": "json_object"}

            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
                logger.warning(f"OpenAI API returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"OpenAI completion failed: {e}")
        return ""

    async def summarize(self, content: str) -> SummarizeResponse:
        prompt = SUMMARIZER_USER_PROMPT.format(content=content[:15000])
        raw = await self.complete(
            prompt=prompt,
            system_prompt=SUMMARIZER_SYSTEM_PROMPT,
            json_schema={"type": "object"},
            temperature=0.1,
        )
        if raw:
            try:
                parsed = _extract_json_from_text(raw)
                if isinstance(parsed, dict) and "summary" in parsed:
                    return SummarizeResponse(
                        title=parsed.get("title", "Structured Knowledge Summary"),
                        summary=parsed.get("summary", ""),
                        key_concepts=parsed.get("key_concepts", []),
                        important_points=parsed.get("important_points", []),
                        practical_example=parsed.get("practical_example"),
                        related_concepts=parsed.get("related_concepts", []),
                        things_to_learn_next=parsed.get("things_to_learn_next", []),
                    )
            except Exception as e:
                logger.warning(f"Failed to parse OpenAI summary: {e}")

        lines = [line.strip() for line in content.split("\n") if line.strip()]
        title = lines[0][:80] if lines else "Note Summary"
        return SummarizeResponse(
            title=title,
            summary=content[:250] + ("..." if len(content) > 250 else ""),
            key_concepts=["Core Concept"],
            important_points=[line[:100] for line in lines[:3]] or ["Key concept overview"],
            practical_example="Review your captured notes to connect related ideas.",
            related_concepts=["Knowledge Management", "System Design"],
            things_to_learn_next=["Explore related concepts in the graph"],
        )

    async def generate_tags(self, content: str) -> list[str]:
        prompt = TAGGER_USER_PROMPT.format(content=content[:10000])
        raw = await self.complete(
            prompt=prompt,
            system_prompt=TAGGER_SYSTEM_PROMPT,
            json_schema={"type": "array"},
            temperature=0.1,
        )
        if raw:
            try:
                parsed = _extract_json_from_text(raw)
                if isinstance(parsed, dict) and "tags" in parsed:
                    return [str(t).strip() for t in parsed["tags"] if str(t).strip()]
                elif isinstance(parsed, list):
                    return [str(t).strip() for t in parsed if str(t).strip()]
            except Exception as e:
                logger.warning(f"Failed to parse tags JSON: {e}")

        words = re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", content)
        tags = list(dict.fromkeys(words))[:4]
        return tags or ["Knowledge", "General"]

    async def extract_concepts(self, content: str) -> list[ExtractedConcept]:
        prompt = CONCEPT_EXTRACTOR_USER_PROMPT.format(content=content[:10000])
        raw = await self.complete(
            prompt=prompt,
            system_prompt=CONCEPT_EXTRACTOR_SYSTEM_PROMPT,
            json_schema={"type": "array"},
            temperature=0.1,
        )
        if raw:
            try:
                parsed = _extract_json_from_text(raw)
                concepts_list = parsed.get("concepts", []) if isinstance(parsed, dict) else parsed
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
                logger.warning(f"Failed to parse concepts: {e}")

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
            existing_concepts=json.dumps(existing_concepts[:40]),
        )
        raw = await self.complete(
            prompt=prompt,
            system_prompt=RELATIONSHIP_EXTRACTOR_SYSTEM_PROMPT,
            json_schema={"type": "array"},
            temperature=0.1,
        )
        if raw:
            try:
                parsed = _extract_json_from_text(raw)
                relationships_list = parsed.get("relationships", []) if isinstance(parsed, dict) else parsed
                results = []
                for item in relationships_list:
                    if isinstance(item, dict) and "source_concept" in item and "target_concept" in item:
                        results.append(
                            DiscoveredRelationship(
                                source_concept=item["source_concept"].strip(),
                                target_concept=item["target_concept"].strip(),
                                relationship_type=item.get("relationship_type", "RELATED_TO"),
                                reason=item.get("reason", "Semantically connected technical concepts."),
                            )
                        )
                if results:
                    return results
            except Exception as e:
                logger.warning(f"Failed to parse relationships: {e}")

        return [
            DiscoveredRelationship(
                source_concept=concepts_to_link[0],
                target_concept=existing_concepts[0],
                relationship_type="RELATED_TO",
                reason="Direct semantic relationship inferred from personal knowledge base.",
            )
        ]

    async def generate_learning_path(
        self,
        topic: str,
        user_known_concepts: list[str],
    ) -> GeneratedLearningPathResponse:
        prompt = LEARNING_PATH_USER_PROMPT.format(
            topic=topic,
            user_known_concepts=json.dumps(user_known_concepts[:30]),
        )
        raw = await self.complete(
            prompt=prompt,
            system_prompt=LEARNING_PATH_SYSTEM_PROMPT,
            json_schema={"type": "object"},
            temperature=0.2,
        )
        if raw:
            try:
                parsed = _extract_json_from_text(raw)
                if isinstance(parsed, dict) and "steps" in parsed:
                    steps = []
                    for s in parsed.get("steps", []):
                        if isinstance(s, dict) and "title" in s:
                            steps.append(
                                GeneratedPathStep(
                                    title=str(s["title"]),
                                    description=str(s.get("description", "")),
                                    concept_name=str(s.get("concept_name", s["title"])),
                                )
                            )
                    if steps:
                        return GeneratedLearningPathResponse(
                            title=parsed.get("title", f"Mastering {topic}"),
                            description=parsed.get("description", f"Step-by-step roadmap for {topic}"),
                            steps=steps,
                        )
            except Exception as e:
                logger.warning(f"Failed to parse learning path: {e}")

        return GeneratedLearningPathResponse(
            title=f"Mastery Roadmap: {topic}",
            description=f"Foundational to advanced curriculum for {topic}",
            steps=[
                GeneratedPathStep(
                    title=f"1. Foundations of {topic}",
                    description="Core definitions, historical context, and architectural principles.",
                    concept_name=topic,
                ),
                GeneratedPathStep(
                    title=f"2. Practical Implementation of {topic}",
                    description="Hands-on coding, patterns, and framework integration.",
                    concept_name=f"{topic} Implementation",
                ),
                GeneratedPathStep(
                    title="3. Advanced Optimization & Production Patterns",
                    description="Scaling, observability, edge cases, and performance tuning.",
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
            "\n---\n".join(
                f"Title: {n.get('title')}\nSummary: {n.get('summary')}\nContent: {n.get('content', '')[:600]}"
                for n in context_notes
            )
            if context_notes
            else "No directly relevant notes stored."
        )
        concepts_str = (
            ", ".join(
                f"{c.get('name')} (Level: {c.get('knowledge_level')})"
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
