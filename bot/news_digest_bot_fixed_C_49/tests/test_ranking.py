from datetime import datetime, timedelta, timezone

from app.domain.policies.ranking import select_primary_article
from app.schemas.articles import NormalizedArticle


def test_should_prefer_english_source_over_russian_for_same_story() -> None:
    now = datetime.now(tz=timezone.utc)
    english = NormalizedArticle(
        provider="a",
        url="https://example.com/en",
        title="BMW starts production",
        description=None,
        source_name="Reuters",
        source_language="en",
        published_at=now,
        normalized_title="bmw starts production",
        canonical_key="bmw starts production",
    )
    russian = NormalizedArticle(
        provider="b",
        url="https://example.com/ru",
        title="BMW starts production",
        description=None,
        source_name="Unknown",
        source_language="ru",
        published_at=now + timedelta(minutes=5),
        normalized_title="bmw starts production",
        canonical_key="bmw starts production",
    )

    assert select_primary_article([english, russian]).url == english.url
