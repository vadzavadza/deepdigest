from datetime import datetime, timezone

from app.application.services.deduplication import group_into_stories, normalize_articles
from app.domain.policies.ranking import select_primary_article
from app.schemas.articles import RawArticle, NormalizedArticle


def test_should_filter_wikipedia_from_candidates() -> None:
    items = [
        RawArticle(
            provider="a",
            url="https://en.wikipedia.org/wiki/BMW",
            title="BMW - Wikipedia",
            description=None,
            source_name="en.wikipedia.org",
            source_language="en",
            published_at=datetime.now(tz=timezone.utc),
        ),
        RawArticle(
            provider="b",
            url="https://www.reuters.com/business/autos-transportation/bmw-launches-new-ev-2026-04-22/",
            title="BMW launches new EV | Reuters",
            description=None,
            source_name="Reuters",
            source_language="en",
            published_at=datetime.now(tz=timezone.utc),
        ),
    ]
    normalized = normalize_articles(items)
    assert len(normalized) == 1
    assert "wikipedia" not in normalized[0].source_name.lower()


def test_should_merge_liveblog_variants_into_single_story() -> None:
    now = datetime.now(tz=timezone.utc)
    items = [
        RawArticle(
            provider="a",
            url="https://news.sky.com/story/ukraine-war-latest-russian-port-on-fire-1",
            title="Ukraine war latest: Russian port on fire day after deadly strike - as Kremlin accuses Europe over nuclear plans | World News | Sky News",
            description="A Russian port caught fire after a deadly strike.",
            source_name="news.sky.com",
            source_language="en",
            published_at=now,
        ),
        RawArticle(
            provider="b",
            url="https://news.sky.com/story/ukraine-war-latest-major-accident-risk-2",
            title="Ukraine war latest: 'Major accident' risk as Kyiv accuses Russia of attacks near Chernobyl | World News | Sky News",
            description="Kyiv accuses Russia of conducting attacks near the Chernobyl nuclear site.",
            source_name="news.sky.com",
            source_language="en",
            published_at=now,
        ),
    ]
    stories = group_into_stories(normalize_articles(items))
    assert len(stories) == 1


def test_should_prefer_reuters_over_weak_source() -> None:
    now = datetime.now(tz=timezone.utc)
    weak = NormalizedArticle(
        provider="a",
        url="https://foxnews.com/article",
        title="BMW starts production",
        description=None,
        source_name="foxnews.com",
        source_language="en",
        published_at=now,
        normalized_title="bmw starts production",
        canonical_key="bmw starts production",
    )
    strong = NormalizedArticle(
        provider="b",
        url="https://reuters.com/article",
        title="BMW starts production",
        description=None,
        source_name="Reuters",
        source_language="en",
        published_at=now,
        normalized_title="bmw starts production",
        canonical_key="bmw starts production",
    )
    assert select_primary_article([weak, strong]).source_name == "Reuters"
