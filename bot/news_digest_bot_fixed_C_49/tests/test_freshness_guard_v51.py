from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.infrastructure.sources.openrouter_web_search import OpenRouterWebSearchSource
from app.search_v2.strategy import build_search_plan


def test_search_plan_uses_explicit_publish_after_date() -> None:
    to_dt = datetime(2026, 4, 25, 12, tzinfo=timezone.utc)
    from_dt = to_dt - timedelta(days=7)
    plan = build_search_plan("Volkswagen", from_dt=from_dt, to_dt=to_dt, first_run=True)
    assert "published after 2026-04-18" in plan.freshness_hint
    assert any("published after 2026-04-18" in query for query in plan.query_variants)


def test_verified_publish_date_prefers_article_metadata() -> None:
    source = object.__new__(OpenRouterWebSearchSource)
    source._require_verified_publish_date = True
    source._allow_weak_publish_dates = False
    html = '<html><head><meta property="article:published_time" content="2026-04-24T10:15:00Z"></head></html>'
    dt, dt_source = source._extract_best_publish_datetime(
        html=html,
        canonical_url="https://example.com/2025/01/01/old-slug",
        last_modified="Fri, 25 Apr 2026 10:00:00 GMT",
    )
    assert dt == datetime(2026, 4, 24, 10, 15, tzinfo=timezone.utc)
    assert dt_source == "metadata"


def test_verified_publish_date_can_use_url_date() -> None:
    source = object.__new__(OpenRouterWebSearchSource)
    source._require_verified_publish_date = True
    source._allow_weak_publish_dates = False
    dt, dt_source = source._extract_best_publish_datetime(
        html="<html></html>",
        canonical_url="https://example.com/news/2026/04/24/volkswagen-results",
        last_modified=None,
    )
    assert dt == datetime(2026, 4, 24, tzinfo=timezone.utc)
    assert dt_source == "url"


def test_missing_publish_date_is_not_faked_from_last_modified_by_default() -> None:
    source = object.__new__(OpenRouterWebSearchSource)
    source._require_verified_publish_date = True
    source._allow_weak_publish_dates = False
    dt, dt_source = source._extract_best_publish_datetime(
        html="<html></html>",
        canonical_url="https://example.com/news/volkswagen-results",
        last_modified="Fri, 25 Apr 2026 10:00:00 GMT",
    )
    assert dt is None
    assert dt_source is None
