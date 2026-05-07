from __future__ import annotations

from datetime import datetime, timezone

from app.application.services.deduplication import group_into_stories, normalize_articles
from app.infrastructure.sources.openrouter_web_search import OpenRouterWebSearchSource
from app.schemas.articles import RawArticle
from app.schemas.sources import RawSourceItem
from app.search_v2.article_filter import is_candidate_article
from app.search_v2.strategy import build_search_plan, classify_topic


def test_cyrillic_sports_match_reports_are_grouped() -> None:
    now = datetime.now(tz=timezone.utc)
    articles = [
        RawArticle(
            provider="a",
            url="https://example.com/2026/04/23/shakhtar-zorya-1",
            title="Чемпіонат України. Шахтар завдяки пенальті переміг Зорю",
            description="Shakhtar won 2-1 against Zorya thanks to a penalty in the Ukrainian Championship.",
            source_name="Dynamo.kiev.ua",
            source_language="uk",
            published_at=now,
        ),
        RawArticle(
            provider="b",
            url="https://example.net/2026/04/23/shakhtar-zorya-2",
            title="Шахтар дотиснув Зорю і зміцнив своє лідерство в Прем'єр-лізі",
            description="Shakhtar secured victory over Zorya thanks to a penalty converted by Artem Bondarenko.",
            source_name="Glavcom",
            source_language="uk",
            published_at=now,
        ),
    ]
    assert len(group_into_stories(normalize_articles(articles))) == 1


def test_reject_topic_news_hub_page() -> None:
    now = datetime.now(tz=timezone.utc)
    plan = build_search_plan("microsoft", from_dt=now, to_dt=now, first_run=True)
    assert not is_candidate_article(
        plan,
        url="https://www.windowscentral.com/microsoft",
        title="Microsoft News | Windows Central",
        description="Latest Microsoft news from Windows Central",
    )


def test_python_is_treated_as_software_topic_not_generic_snake() -> None:
    assert classify_topic("python") == "technology"
    now = datetime.now(tz=timezone.utc)
    plan = build_search_plan("python", from_dt=now, to_dt=now, first_run=True)
    joined = " ".join(plan.query_variants).lower()
    assert "programming language" in joined or "software" in joined
    assert not is_candidate_article(
        plan,
        url="https://example.com/2026/04/25/giant-python-found-in-zoo",
        title="Giant python found in city zoo",
        description="A reptile escaped from its enclosure.",
    )


def test_esports_acronym_query_is_esports() -> None:
    assert classify_topic("BLAST CS") == "esports"


def test_search_snippet_fallback_is_high_confidence_only() -> None:
    source = object.__new__(OpenRouterWebSearchSource)
    source._require_verified_publish_date = True
    source._allow_undated_fallback = False
    source._debug_rejections = False
    source._max_article_age_hours = 168
    source._future_skew_hours = 12
    source._search_snippet_fallback_min_directness = 12
    source._search_snippet_fallback_min_confidence = 2

    now = datetime(2026, 4, 26, 12, tzinfo=timezone.utc)
    plan = build_search_plan("microsoft", from_dt=now, to_dt=now, first_run=True)
    item = RawSourceItem(
        provider="openrouter_web_search",
        url="https://example.com/2026/04/26/microsoft-security-update",
        title="Microsoft releases security update for Windows developers",
        description="Microsoft published a new software security update affecting Windows developer tools.",
        source_name="example.com",
        published_at=None,
        metadata={"search_annotation": True, "search_snippet": True},
    )
    accepted = source._fallback_candidate(
        item,
        from_dt=now,
        to_dt=now,
        plan=plan,
        reason="test",
        allow_search_snippet_fallback=True,
    )
    assert accepted is not None
    assert accepted.metadata["published_at_source"] in {"url", "search_snippet"}
