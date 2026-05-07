from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.topic_processing import TopicProcessingService
from app.infrastructure.db.session import get_session
from app.infrastructure.llm.openrouter import OpenRouterProvider
from app.infrastructure.repositories.topics import TopicRepository
from app.infrastructure.sources.factory import build_source_registry
from app.infrastructure.telegram.publisher import TelegramPublisher
from telegram import Bot

router = APIRouter()


class ProcessTopicRequest(BaseModel):
    force: bool = False
    window_override_hours: int | None = None


@router.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@router.get('/topics/{topic_id}')
async def get_topic(topic_id: int, session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    repo = TopicRepository(session)
    topic = await repo.get_by_id(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail='Topic not found')

    return {
        'id': topic.id,
        'query_text': topic.query_text,
        'output_language': topic.output_language,
        'timezone': topic.timezone,
        'mode': topic.mode,
        'is_active': topic.is_active,
    }


@router.post('/process-topic/{topic_id}')
async def process_topic(
    topic_id: int,
    request: ProcessTopicRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    from app.shared.settings import get_settings
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    service = TopicProcessingService(
        session=session,
        source_registry=build_source_registry(),
        llm_provider=OpenRouterProvider(),
        publisher=TelegramPublisher(bot),
    )
    try:
        outcome = await service.process_topic(
            topic_id=topic_id,
            force=request.force,
            window_override_hours=request.window_override_hours,
        )
    finally:
        await bot.session.close()
    return {
        'topic_id': topic_id,
        'status': 'accepted',
        'run_mode': 'manual',
        'found_articles': outcome.found_articles,
        'unique_stories': outcome.unique_stories,
        'sent_count': outcome.sent_count,
        'budget_spent_usd': round(outcome.budget_spent_usd, 6),
        'budget_remaining_usd': round(outcome.budget_remaining_usd, 6),
        'budget_over_soft_limit': outcome.budget_over_soft_limit,
    }
