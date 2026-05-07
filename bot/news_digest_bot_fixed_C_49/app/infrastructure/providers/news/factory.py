from app.infrastructure.providers.news.base import NewsProvider
from app.infrastructure.providers.news.mock import MockNewsProvider


def build_news_providers() -> list[NewsProvider]:
    # TODO: replace MockNewsProvider with real provider adapters after provider selection.
    return [MockNewsProvider()]
