from app.infrastructure.sources.base import SourceAdapter
from app.infrastructure.sources.mock import MockSourceAdapter
from app.infrastructure.sources.openrouter_web_search import OpenRouterWebSearchSource
from app.infrastructure.sources.registry import SourceRegistry
from app.infrastructure.sources.rss import RssSource
from app.infrastructure.sources.telegram_channel import TelegramChannelSource
from app.shared.cost_budget import CostBudget
from app.shared.settings import get_settings


def build_source_registry(*, budget: CostBudget | None = None) -> SourceRegistry:
    settings = get_settings()
    adapters: list[SourceAdapter] = []

    if settings.enable_openrouter_web_search_source and settings.openrouter_api_key:
        adapters.append(OpenRouterWebSearchSource(budget=budget))

    if settings.enable_telegram_channel_source:
        adapters.append(TelegramChannelSource())

    if settings.enable_rss_source:
        adapters.append(RssSource())

    if settings.enable_mock_source or not adapters:
        adapters.append(MockSourceAdapter())

    return SourceRegistry(adapters)
