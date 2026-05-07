from __future__ import annotations

from app.domain.enums import SourceType
from app.infrastructure.sources.registry import SourceRegistry
from app.schemas.discovery import SourceCollectionResult, SourceFetchRequest, SourceFetchStats
from app.schemas.sources import RawSourceItem
from app.shared.logging import get_logger

logger = get_logger(__name__)


class SourceCollectionService:
    def __init__(self, registry: SourceRegistry) -> None:
        self._registry = registry

    async def collect(self, request: SourceFetchRequest) -> tuple[list[RawSourceItem], SourceCollectionResult]:
        items: list[RawSourceItem] = []
        stats: list[SourceFetchStats] = []

        for adapter in self._registry.adapters:
            try:
                fetched = await adapter.fetch(
                    query=request.query,
                    from_dt=request.from_dt,
                    to_dt=request.to_dt,
                    limit=request.limit,
                )
                items.extend(fetched)
                stats.append(
                    SourceFetchStats(
                        source_name=adapter.name,
                        source_type=adapter.source_type,
                        fetched_count=len(fetched),
                    )
                )
                logger.info(
                    'source_fetch',
                    source_name=adapter.name,
                    source_type=adapter.source_type.value,
                    raw_count=len(fetched),
                    status='ok',
                )
            except Exception as exc:
                stats.append(
                    SourceFetchStats(
                        source_name=getattr(adapter, 'name', 'unknown'),
                        source_type=getattr(adapter, 'source_type', SourceType.OTHER),
                        failed=True,
                        error_message=str(exc),
                    )
                )
                logger.warning(
                    'source_fetch_failed',
                    source_name=getattr(adapter, 'name', 'unknown'),
                    error=str(exc),
                )

        result = SourceCollectionResult(items_count=len(items), stats=stats)
        return items, result
