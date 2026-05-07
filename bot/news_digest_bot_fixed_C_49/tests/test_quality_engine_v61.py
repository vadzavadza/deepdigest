from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.policies.ranking import source_authority_tier, source_quality_weight
from app.search_v2.core import CandidateStatus, FreshnessPolicy, evaluate_candidate
from app.search_v2.strategy import build_search_plan


def _now() -> datetime:
    return datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)


def test_fetch_blocked_strong_title_can_be_weak_but_usable_without_snippet() -> None:
    now = _now()
    plan = build_search_plan("Audi", from_dt=now - timedelta(days=7), to_dt=now, first_run=True)
    decision = evaluate_candidate(
        plan,
        url="https://www.autoblog.com/news/audis-usa-sales-q1-2026/",
        title="Audi's Only U.S. Sales Winners Are Sedans as Sales Drop 30% - Autoblog",
        description=None,
        published_at=None,
        published_at_source=None,
        to_dt=now,
        policy=FreshnessPolicy(weak_min_article_confidence=2),
        search_annotation=True,
        search_snippet=False,
    )
    assert decision.status == CandidateStatus.WEAK_BUT_USABLE


def test_price_or_market_page_title_only_is_not_weak_usable() -> None:
    now = _now()
    plan = build_search_plan("bitcoin", from_dt=now - timedelta(days=7), to_dt=now, first_run=True)
    decision = evaluate_candidate(
        plan,
        url="https://www.forbes.com/advisor/investing/cryptocurrency/bitcoin-price-today/",
        title="Bitcoin Price Today: BTC is trading at $74,217 – Forbes Advisor",
        description=None,
        published_at=None,
        published_at_source=None,
        to_dt=now,
        policy=FreshnessPolicy(weak_min_article_confidence=2),
        search_annotation=True,
        search_snippet=False,
    )
    assert decision.status == CandidateStatus.REJECTED


def test_low_authority_exchange_sources_are_penalized() -> None:
    assert source_quality_weight("weex.com") < 0
    assert source_authority_tier("weex.com") == "weak"
    assert source_authority_tier("apnews.com") == "strong"
