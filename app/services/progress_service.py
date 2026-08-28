from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept, KnowledgeLevel
from app.models.learning_path import LearningPath, LearningPathItem, PathItemStatus
from app.models.note import Note
from app.models.relationship import ConceptRelationship
from app.models.tag import Tag
from app.schemas.progress import (
    ConceptLevelCount,
    GrowthDataPoint,
    PathProgressSummary,
    ProgressMetricsOut,
    RecentKnowledgeItem,
)


class ProgressService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_metrics(self, user_id: str) -> ProgressMetricsOut:
        # Total counts
        notes_res = await self.db.execute(select(func.count(Note.id)).where(Note.user_id == user_id))
        total_notes = notes_res.scalar() or 0

        concepts_res = await self.db.execute(select(func.count(Concept.id)).where(Concept.user_id == user_id))
        total_concepts = concepts_res.scalar() or 0

        tags_res = await self.db.execute(select(func.count(Tag.id)).where(Tag.user_id == user_id))
        total_tags = tags_res.scalar() or 0

        rels_res = await self.db.execute(
            select(func.count(ConceptRelationship.id)).where(ConceptRelationship.user_id == user_id)
        )
        total_connections = rels_res.scalar() or 0

        paths_res = await self.db.execute(
            select(func.count(LearningPath.id)).where(LearningPath.user_id == user_id)
        )
        total_paths = paths_res.scalar() or 0

        # Concepts by level
        level_counts_stmt = (
            select(Concept.knowledge_level, func.count(Concept.id))
            .where(Concept.user_id == user_id)
            .group_by(Concept.knowledge_level)
        )
        level_res = await self.db.execute(level_counts_stmt)
        level_dict = {lvl: count for lvl, count in level_res.all()}

        concepts_by_level = [
            ConceptLevelCount(level=lvl.value, count=level_dict.get(lvl, 0))
            for lvl in KnowledgeLevel
        ]

        completed_concepts = level_dict.get(KnowledgeLevel.STRONG, 0)
        learning_concepts = (
            level_dict.get(KnowledgeLevel.LEARNING, 0)
            + level_dict.get(KnowledgeLevel.INTERMEDIATE, 0)
            + level_dict.get(KnowledgeLevel.FAMILIAR, 0)
        )

        # Learning paths progress
        paths_stmt = select(LearningPath).where(LearningPath.user_id == user_id)
        paths_data = (await self.db.execute(paths_stmt)).scalars().all()
        paths_progress: list[PathProgressSummary] = []

        for p in paths_data:
            items_stmt = select(LearningPathItem).where(LearningPathItem.learning_path_id == p.id)
            items = (await self.db.execute(items_stmt)).scalars().all()
            total_it = len(items)
            completed_it = sum(1 for it in items if it.status == PathItemStatus.COMPLETED)
            pct = round((completed_it / total_it * 100.0), 1) if total_it > 0 else 0.0
            paths_progress.append(
                PathProgressSummary(
                    id=p.id,
                    title=p.title,
                    total_items=total_it,
                    completed_items=completed_it,
                    progress_percentage=pct,
                )
            )

        # Growth timeline (Notes & Concepts grouped by date)
        growth_map: dict[str, dict[str, int]] = defaultdict(lambda: {"notes": 0, "concepts": 0})

        all_notes = (
            await self.db.execute(
                select(Note.created_at).where(Note.user_id == user_id).order_by(Note.created_at.asc())
            )
        ).scalars().all()
        for created in all_notes:
            d_str = created.strftime("%Y-%m-%d")
            growth_map[d_str]["notes"] += 1

        all_concepts = (
            await self.db.execute(
                select(Concept.created_at).where(Concept.user_id == user_id).order_by(Concept.created_at.asc())
            )
        ).scalars().all()
        for created in all_concepts:
            d_str = created.strftime("%Y-%m-%d")
            growth_map[d_str]["concepts"] += 1

        # Calculate cumulative growth
        growth_timeline: list[GrowthDataPoint] = []
        cum_notes = 0
        cum_concepts = 0
        for date_key in sorted(growth_map.keys()):
            cum_notes += growth_map[date_key]["notes"]
            cum_concepts += growth_map[date_key]["concepts"]
            growth_timeline.append(
                GrowthDataPoint(
                    date=date_key,
                    notes_count=cum_notes,
                    concepts_count=cum_concepts,
                )
            )

        if not growth_timeline:
            today_str = datetime.now(UTC).strftime("%Y-%m-%d")
            growth_timeline.append(
                GrowthDataPoint(date=today_str, notes_count=total_notes, concepts_count=total_concepts)
            )

        # Recent Knowledge (Latest notes and concepts combined)
        recent_notes_stmt = (
            select(Note).where(Note.user_id == user_id).order_by(Note.created_at.desc()).limit(5)
        )
        recent_notes = (await self.db.execute(recent_notes_stmt)).scalars().all()

        recent_concepts_stmt = (
            select(Concept).where(Concept.user_id == user_id).order_by(Concept.created_at.desc()).limit(5)
        )
        recent_concepts = (await self.db.execute(recent_concepts_stmt)).scalars().all()

        recent_knowledge: list[RecentKnowledgeItem] = []
        for n in recent_notes:
            recent_knowledge.append(
                RecentKnowledgeItem(
                    id=n.id,
                    type="note",
                    title=n.title,
                    timestamp=n.created_at,
                    badge="Note",
                )
            )
        for c in recent_concepts:
            recent_knowledge.append(
                RecentKnowledgeItem(
                    id=c.id,
                    type="concept",
                    title=c.name,
                    timestamp=c.created_at,
                    badge=c.knowledge_level.value,
                )
            )

        recent_knowledge.sort(key=lambda x: x.timestamp, reverse=True)

        return ProgressMetricsOut(
            total_notes=total_notes,
            total_concepts=total_concepts,
            total_tags=total_tags,
            total_connections=total_connections,
            total_learning_paths=total_paths,
            completed_concepts=completed_concepts,
            learning_concepts=learning_concepts,
            concepts_by_level=concepts_by_level,
            learning_paths_progress=paths_progress,
            growth_timeline=growth_timeline,
            recent_knowledge=recent_knowledge[:8],
        )
