import asyncio
import logging

from app.db.session import AsyncSessionLocal
from app.services.knowledge_pipeline import run_note_processing_pipeline
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.process_note_task")
def process_note_task(note_id: str, user_id: str):
    """Celery background worker task for note processing."""
    async def _async_run():
        async with AsyncSessionLocal() as session:
            await run_note_processing_pipeline(note_id=note_id, user_id=user_id, db=session)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_async_run())
        else:
            loop.run_until_complete(_async_run())
    except Exception:
        asyncio.run(_async_run())
