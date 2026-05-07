from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.search_v2.core import CandidateStatus, FreshnessPolicy, evaluate_candidate
from app.search_v2.strategy import build_search_plan, canonicalize_topic
from app.search_v2.article_filter import candidate_quality


def _now() -> datetime:
    return datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)


def test_generic_suffixes_do_not_become_required_entity_tokens() -> None:
    assert canonicalize_topic("NAVI TEAM") == "navi"
    assert canonicalize_topic("Rome city") == "rome"


def test_team_articles_do_not_need_exact_user_phrase() -> None:
    now = _now()
    plan = build_search_plan("NAVI TEAM", from_dt=now - timedelta(days=7), to_dt=now, first_run=True)
    quality = candidate_quality(
        plan,
        url="https://csgo.com/news/130041-navi-announce-updated-cs2-roster-jl-goes-inactive",
        title="NAVI announce updated CS2 roster – jL goes inactive",
        description="NAVI announce an updated CS2 roster before the tournament",
    )
    assert quality.accepted
    assert quality.reason is None


def test_direct_search_annotation_without_verified_date_can_be_weak_but_usable() -> None:
    now = _now()
    plan = build_search_plan("NAVI TEAM", from_dt=now - timedelta(days=7), to_dt=now, first_run=True)
    decision = evaluate_candidate(
        plan,
        url="https://csgo.com/news/130041-navi-announce-updated-cs2-roster-jl-goes-inactive",
        title="NAVI announce updated CS2 roster – jL goes inactive",
        description="NAVI announce an updated CS2 roster before the tournament",
        published_at=None,
        published_at_source=None,
        to_dt=now,
        policy=FreshnessPolicy(),
        search_annotation=True,
        search_snippet=True,
    )
    assert decision.status == CandidateStatus.WEAK_BUT_USABLE


def test_verified_article_just_outside_soft_window_is_accepted_not_zeroed() -> None:
    now = _now()
    plan = build_search_plan("bitcoin", from_dt=now - timedelta(days=7), to_dt=now, first_run=True)
    decision = evaluate_candidate(
        plan,
        url="https://news.bitcoin.com/bitcoin-rebounds-but-cryptos-security-crisis-intensifies-week-in-review/",
        title="Bitcoin Rebounds, But Crypto’s Security Crisis Intensifies – Week in Review",
        description="Bitcoin rebounds as crypto security concerns intensify.",
        published_at=now - timedelta(days=7, hours=1),
        published_at_source="metadata",
        to_dt=now,
        policy=FreshnessPolicy(),
    )
    assert decision.status == CandidateStatus.ACCEPTED
    assert decision.reason == "accepted_verified_recent_but_not_latest"


def test_very_old_article_is_still_rejected() -> None:
    now = _now()
    plan = build_search_plan("bitcoin", from_dt=now - timedelta(days=7), to_dt=now, first_run=True)
    decision = evaluate_candidate(
        plan,
        url="https://abcnews.com/Business/bitcoins-slide-investors-worried/story?id=119166107",
        title="What's behind bitcoin's slide and should investors be worried?",
        description="Investors are worried about bitcoin.",
        published_at=now - timedelta(days=400),
        published_at_source="metadata",
        to_dt=now,
        policy=FreshnessPolicy(),
    )
    assert decision.status == CandidateStatus.OLD
