from datetime import UTC, datetime, timedelta

from app.application.services.source_collection import SourceCollectionService
from app.infrastructure.sources.mock import MockSourceAdapter
from app.infrastructure.sources.registry import SourceRegistry
from app.schemas.discovery import SourceFetchRequest
from app.schemas.sources import RawSourceItem


async def test_should_collect_items_from_registered_sources():
    now = datetime.now(tz=UTC)
    adapter = MockSourceAdapter(
        items=[
            RawSourceItem(
                provider='mock',
                url='https://example.com/story-1',
                title='BMW launches new platform',
                description='desc',
                source_name='Example',
                source_language='en',
                published_at=now,
            )
        ]
    )
    service = SourceCollectionService(SourceRegistry([adapter]))

    items, result = await service.collect(
        SourceFetchRequest(
            query='BMW',
            from_dt=now - timedelta(hours=1),
            to_dt=now + timedelta(hours=1),
            limit=10,
        )
    )

    assert len(items) == 1
    assert result.items_count == 1
    assert result.stats[0].fetched_count == 1



def test_broad_topic_query_expansion_for_auto_brand() -> None:
    from app.infrastructure.sources.openrouter_web_search import OpenRouterWebSearchSource
    now = datetime.now(tz=UTC)
    queries = OpenRouterWebSearchSource._build_queries("BMW", now - timedelta(hours=24), now)
    joined = " ".join(queries).lower()
    # Universal quality engine should not hard-code model names for one brand.
    # It should keep brand queries news/business-oriented and date-bounded.
    assert "bmw" in joined
    assert "published after" in joined
    assert "reuters" in joined or "bloomberg" in joined or "cnbc" in joined
