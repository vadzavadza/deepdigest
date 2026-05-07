from datetime import datetime

from app.schemas.articles import RawArticle


class MockNewsProvider:
    name = "mock"

    def __init__(self, articles: list[RawArticle] | None = None) -> None:
        self._articles = articles or []

    async def search(
        self,
        query: str,
        from_dt: datetime,
        to_dt: datetime,
        limit: int,
    ) -> list[RawArticle]:
        filtered = [
            article
            for article in self._articles
            if from_dt <= article.published_at <= to_dt and query.lower() in article.title.lower()
        ]
        return filtered[:limit]
