from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.application.services.deduplication import group_into_stories, normalize_articles
from app.infrastructure.sources.openrouter_web_search import OpenRouterWebSearchSource
from app.schemas.articles import RawArticle
from app.search_v2.strategy import build_search_plan


def test_budget_prefers_three_smaller_search_passes_under_seven_cents() -> None:
    source = object.__new__(OpenRouterWebSearchSource)
    source._search_result_cost_usd = 0.004
    source._topic_budget_usd = 0.07
    source._max_calls_per_topic = 3

    assert source._allowed_search_calls(results_per_call=5) == 3


def test_esports_counter_strike_expansion_is_in_first_three_passes() -> None:
    to_dt = datetime(2026, 4, 26, 12, tzinfo=timezone.utc)
    plan = build_search_plan("BLAST CS", from_dt=to_dt - timedelta(days=7), to_dt=to_dt, first_run=True)

    first_three = " ".join(plan.query_variants[:3]).lower()
    assert plan.topic_kind == "esports"
    assert "counter-strike" in first_three or "cs2" in first_three


def test_payload_extraction_keeps_niche_article_candidate_before_local_validation() -> None:
    source = object.__new__(OpenRouterWebSearchSource)
    payload = {
        "choices": [
            {
                "message": {
                    "annotations": [
                        {
                            "url_citation": {
                                "url": "https://example-esports.com/events/blast-cs-roster-update",
                                "title": "BLAST CS announces new Counter-Strike tournament format",
                                "content": "BLAST CS confirmed a Counter-Strike tournament update this week.",
                            }
                        }
                    ]
                }
            }
        ]
    }

    items = source._extract_items_from_payload(payload, limit=5)
    assert len(items) == 1
    assert "Counter-Strike" in items[0].title


def test_cyrillic_match_reports_with_different_verbs_still_dedup() -> None:
    now = datetime(2026, 4, 26, tzinfo=timezone.utc)
    articles = [
        RawArticle(
            provider="a",
            url="https://a.example/2026/04/23/shakhtar-zorya-penalty",
            title="Чемпіонат України. Шахтар завдяки пенальті переміг Зорю",
            description="Шахтар переміг Зорю у перенесеному матчі чемпіонату України.",
            source_name="a.example",
            source_language="uk",
            published_at=now,
        ),
        RawArticle(
            provider="b",
            url="https://b.example/2026/04/23/shakhtar-zorya-premier-league",
            title="Шахтар дотиснув Зорю і зміцнив своє лідерство в Прем'єр-лізі",
            description="Шахтар переміг завдяки пенальті у матчі проти Зорі.",
            source_name="b.example",
            source_language="uk",
            published_at=now,
        ),
    ]

    assert len(group_into_stories(normalize_articles(articles))) == 1
