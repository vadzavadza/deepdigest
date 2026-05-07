from datetime import datetime, timezone

from app.application.services.deduplication import group_into_stories, normalize_articles
from app.schemas.articles import RawArticle


def test_should_group_similar_titles_into_single_story() -> None:
    articles = [
        RawArticle(
            provider="a",
            url="https://example.com/1",
            title="BMW launches new EV in Berlin",
            description=None,
            source_name="Reuters",
            source_language="en",
            published_at=datetime.now(tz=timezone.utc),
        ),
        RawArticle(
            provider="b",
            url="https://example.com/2",
            title="BMW launches new electric vehicle in Berlin",
            description=None,
            source_name="DW",
            source_language="en",
            published_at=datetime.now(tz=timezone.utc),
        ),
    ]
    stories = group_into_stories(normalize_articles(articles))
    assert len(stories) == 1



def test_should_group_cross_language_like_titles_with_shared_entities_into_single_story() -> None:
    articles = [
        RawArticle(
            provider="a",
            url="https://example.com/a",
            title="Real Madrid are UEFA Youth League champions again",
            description="Club Brugge beaten in final",
            source_name="AP",
            source_language="en",
            published_at=datetime.now(tz=timezone.utc),
        ),
        RawArticle(
            provider="b",
            url="https://example.com/b",
            title="El Real Madrid se convierte en campeón de la Youth League",
            description="Real Madrid ganó la final de Youth League",
            source_name="Cadena SER",
            source_language="es",
            published_at=datetime.now(tz=timezone.utc),
        ),
    ]
    stories = group_into_stories(normalize_articles(articles))
    assert len(stories) == 1
