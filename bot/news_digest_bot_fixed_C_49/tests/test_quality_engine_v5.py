from datetime import datetime, timedelta, timezone

from app.search_v2.article_filter import candidate_quality, is_candidate_article
from app.search_v2.strategy import build_search_plan, classify_topic


def _plan(query: str):
    now = datetime.now(tz=timezone.utc)
    return build_search_plan(query, from_dt=now - timedelta(days=7), to_dt=now, first_run=True)


def test_common_geo_region_is_not_treated_as_person() -> None:
    assert classify_topic("Pacific Ocean") == "geo_region"


def test_indirect_country_article_is_rejected_locally() -> None:
    plan = _plan("Iran")
    assert not is_candidate_article(
        plan,
        url="https://example.com/2026/04/23/us-retail-sales-gas-prices",
        title="US retail sales slow as gas prices rise",
        description="Oil markets were affected by tensions in the Middle East, including Iran.",
    )
    quality = candidate_quality(
        plan,
        url="https://example.com/2026/04/23/us-retail-sales-gas-prices",
        title="US retail sales slow as gas prices rise",
        description="Oil markets were affected by tensions in the Middle East, including Iran.",
    )
    assert quality.reason == "indirect_relevance"


def test_city_wrong_context_is_rejected() -> None:
    plan = _plan("Odessa")
    assert plan.normalized_query == "odesa"
    assert not is_candidate_article(
        plan,
        url="https://example.com/2026/04/23/odessa-texas-high-school-baseball",
        title="Odessa Texas high school baseball team reaches playoffs",
        description="Local sports in Odessa, Texas.",
    )


def test_evergreen_guide_is_rejected_for_news_digest() -> None:
    plan = _plan("Rome city")
    assert not is_candidate_article(
        plan,
        url="https://example.com/travel/2026/04/23/things-to-do-in-rome",
        title="Things to do in Rome this weekend",
        description="Travel guide with best restaurants and hotels.",
    )


def test_direct_business_news_is_accepted() -> None:
    plan = _plan("BMW")
    assert is_candidate_article(
        plan,
        url="https://example.com/business/2026/04/23/bmw-opens-new-battery-plant",
        title="BMW opens new battery plant as EV production expands",
        description="The company said the new factory will support upcoming electric models.",
    )
