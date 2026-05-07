from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.policies.ranking import source_quality_weight
from app.search_v2.article_filter import candidate_quality
from app.search_v2.strategy import build_search_plan, classify_topic


def _now() -> datetime:
    return datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)


def test_v62_topic_classifier_understands_verticals() -> None:
    assert classify_topic("Real Madrid") == "sports_team"
    assert classify_topic("Universal Pictures") == "entertainment_company"
    assert classify_topic("Lexus") == "brand_company"
    assert classify_topic("Audi") == "brand_company"
    assert classify_topic("Leonardo DiCaprio") == "person"


def test_v62_short_acronym_is_ambiguous_not_generic_team() -> None:
    assert classify_topic("CS") == "ambiguous_acronym"
    now = _now()
    plan = build_search_plan("CS", from_dt=now - timedelta(days=7), to_dt=now, first_run=True)
    assert any("Counter-Strike" in q for q in plan.query_variants)


def test_v62_cs_requires_counter_strike_context() -> None:
    now = _now()
    plan = build_search_plan("CS", from_dt=now - timedelta(days=7), to_dt=now, first_run=True)
    generic = candidate_quality(
        plan,
        url="https://example.com/news/2026/04/rankings",
        title="Best computer science programs ranked this week",
        description="Computer science university rankings were published.",
    )
    assert not generic.accepted
    assert generic.reason in {"wrong_entity_context", "ambiguous_acronym_without_context"}

    esports = candidate_quality(
        plan,
        url="https://example.com/news/2026/04/cs2-major-roster-update",
        title="CS2 Major roster update for Counter-Strike team",
        description="Counter-Strike esports roster news ahead of the tournament.",
    )
    assert esports.accepted


def test_v62_reviews_are_not_latest_news_for_brands() -> None:
    now = _now()
    plan = build_search_plan("Lexus", from_dt=now - timedelta(days=7), to_dt=now, first_run=True)
    review = candidate_quality(
        plan,
        url="https://example.com/news/2026/04/lexus-rx-review",
        title="I drove the Lexus RX 450h+ for a week — here is what I found",
        description="A week-long review of the Lexus plug-in hybrid SUV.",
    )
    assert not review.accepted
    assert review.reason == "review_or_buying_guide"

    recall = candidate_quality(
        plan,
        url="https://example.com/news/2026/04/lexus-recall-fuel-pump",
        title="Lexus Recalls Vehicles Due to fuel pump failure",
        description="Toyota is recalling Lexus vehicles over a safety defect.",
    )
    assert recall.accepted


def test_v62_vertical_source_authority_adjusts_by_topic_kind() -> None:
    assert source_quality_weight("variety.com", "entertainment_company") > source_quality_weight("newsminimalist.com", "entertainment_company")
    assert source_quality_weight("carscoops.com", "brand_company") > source_quality_weight("tomsguide.com", "brand_company")
    assert source_quality_weight("espn.com", "sports_team") > source_quality_weight("fourfourtwo.com", "sports_team")
