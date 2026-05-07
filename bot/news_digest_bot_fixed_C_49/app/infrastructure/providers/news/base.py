from typing import Protocol
from datetime import datetime

from app.schemas.articles import RawArticle


class NewsProvider(Protocol):
    name: str

    async def search(
        self,
        query: str,
        from_dt: datetime,
        to_dt: datetime,
        limit: int,
    ) -> list[RawArticle]:
        ...
