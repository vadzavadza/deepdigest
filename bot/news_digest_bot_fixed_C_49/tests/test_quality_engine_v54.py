from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.search_v2.article_filter import candidate_quality
from app.search_v2.strategy import build_search_plan, canonicalize_topic, classify_topic


def _plan(query: str):
    to_dt = datetime(2026, 4, 26, 12, tzinfo=timezone.utc)
    return build_search_plan(query, from_dt=to_dt - timedelta(days=7), to_dt=to_dt, first_run=True)


def test_latin_and_cyrillic_city_forms_share_canonical_topic_and_queries() -> None:
    latin = _plan("paris")
    cyrillic = _plan("Париж")

    assert latin.normalized_query == "paris"
    assert cyrillic.normalized_query == "paris"
    assert latin.topic_kind == "city"
    assert cyrillic.topic_kind == "city"
    assert any("paris france" in q.lower() for q in latin.query_variants[:3])
    assert any("париж" in q.lower() for q in cyrillic.query_variants[:3])
    assert "париж" in cyrillic.alternate_terms


def test_cyrillic_brand_typo_can_retrieve_latin_brand_context() -> None:
    plan = _plan("дайсан")

    assert plan.normalized_query == "dyson"
    assert plan.topic_kind == "business"
    assert any('"dyson"' in q.lower() for q in plan.query_variants[:2])
    assert "дайсан" in plan.alternate_terms


def test_public_name_shorthand_normalizes_to_person_without_topic_specific_ranking() -> None:
    for query in ["Trump", "Трамп", "Pavel Durov", "Павел Дуров"]:
        plan = _plan(query)
        assert plan.topic_kind == "person"
        assert plan.normalized_query in {"donald trump", "pavel durov"}
        assert len(plan.query_variants) >= 3


def test_provider_freshness_hint_is_retrieval_broad_not_hard_date_filter() -> None:
    plan = _plan("Dyson")

    hint = plan.freshness_hint.lower()
    assert "published after" not in hint
    assert "recent news" in hint


def test_cyrillic_alternate_terms_count_as_direct_topic_evidence() -> None:
    plan = _plan("Париж")
    quality = candidate_quality(
        plan,
        url="https://example.com/news/2026/04/26/paris-rentals",
        title="Париж вводит новые ограничения для аренды жилья",
        description="Власти Парижа объявили новые правила для туристического жилья.",
    )

    assert quality.accepted, quality.reason
    assert quality.directness_score >= plan.minimum_directness
